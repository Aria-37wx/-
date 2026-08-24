# -*- coding: utf-8 -*-
"""物料管理 Web 界面"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
from warehouse_mcp.db.database import init_db, get_db, CATEGORIES, get_category_subs
from warehouse_mcp.tools.add_material import add_material
from warehouse_mcp.tools.checkout import checkout
from warehouse_mcp.tools.return_item import return_item
from warehouse_mcp.tools.search_materials import search_materials, search_material_rows
from warehouse_mcp.tools.borrow_query import get_borrow_records
from warehouse_mcp.tools.smart_add_material import smart_add_material, infer_material_info
from warehouse_mcp.tools.recommend import analyze_project
from warehouse_mcp.tools.intent_router import classify_intent, classify_intent_fake
from warehouse_mcp.llm_client import configure as llm_configure, get_config_status

st.set_page_config(page_title="物料管理系统", layout="wide")
init_db()

CATEGORY_NAMES = list(CATEGORIES.keys())

# ---- 侧边栏 ----
st.sidebar.title("物料管理系统")
page = st.sidebar.radio("功能导航", ["库存总览", "AI 对话", "入库", "出库", "归还", "记录查询", "标签管理"],
                        label_visibility="visible")

conn = get_db()
try:
    total_types = conn.execute("SELECT COUNT(*) FROM materials").fetchone()[0]
    total_items = conn.execute("SELECT COALESCE(SUM(quantity), 0) FROM materials").fetchone()[0]
    active_borrows = conn.execute("SELECT COUNT(*) FROM borrow_records WHERE status='active'").fetchone()[0]
    total_tags = conn.execute("SELECT COUNT(*) FROM tags").fetchone()[0]
finally:
    conn.close()
st.sidebar.divider()
st.sidebar.metric("物料总数", total_types)
st.sidebar.metric("可用库存", total_items)
st.sidebar.metric("借出中", active_borrows)
st.sidebar.metric("标签库", total_tags)


def _reset_ai_rec_state():
    """清掉推荐结果和批量出库控件状态（每次新推荐前调用，避免旧状态串到新结果）"""
    st.session_state.ai_rec_result = None
    for k in list(st.session_state.keys()):
        if k in ("ai_rec_select", "ai_rec_mode", "ai_rec_phone") or k.startswith("ai_rec_qty_"):
            del st.session_state[k]


def _group_search_rows(rows):
    """把搜索结果聚合成可批量出库的条目。

    - 非耗材：同名（+同大类+同子类+同型号）合并为一条，库存求和，
      matched 保留每条独立编号的记录（批量出库时逐件处理）。
    - 耗材：本身合并存储，每条独立成项。
    """
    non_cons = {}
    items = []
    for r in rows:
        if r["is_consumable"]:
            items.append({
                "name": r["name"], "category": r["category"],
                "sub_category": r["sub_category"], "model": r["model"],
                "is_consumable": True, "location": r["location"] or "",
                "available_qty": r["quantity"], "matched": [dict(r)],
            })
        else:
            key = (r["name"], r["category"], r["sub_category"], r["model"])
            if key not in non_cons:
                non_cons[key] = {
                    "name": r["name"], "category": r["category"],
                    "sub_category": r["sub_category"], "model": r["model"],
                    "is_consumable": False, "location": r["location"] or "",
                    "available_qty": 0, "matched": [],
                }
            non_cons[key]["available_qty"] += r["quantity"]
            non_cons[key]["matched"].append(dict(r))
            if r["location"]:
                non_cons[key]["location"] = r["location"]
    items.extend(non_cons.values())
    items.sort(key=lambda x: (x["category"], x["name"]))
    return items

# ==================== 库存总览 ====================
if page == "库存总览":
    st.header("库存总览")

    col1, col2, col3 = st.columns(3)
    with col1:
        keyword = st.text_input("搜索关键词", placeholder="名称/类别/型号...")
    with col2:
        cat_filter = st.selectbox("大类筛选", ["全部"] + CATEGORY_NAMES)
    with col3:
        tag_filter = st.text_input("标签搜索", placeholder="如：ESP32、WiFi...")

    st.caption('标签搜索会匹配标签名和标签描述（如搜"WiFi"会找到 ESP32 标签）')

    result = search_materials(
        keyword=keyword.strip(),
        category=cat_filter if cat_filter != "全部" else "",
        tag=tag_filter.strip()
    )
    if "没有找到" in result:
        st.info(result)
    else:
        st.text(result)

# ==================== AI 对话 ====================
elif page == "AI 对话":
    st.header("AI 助手")
    st.caption("用自然语言和我对话，我会自动判断你要入库、出库、查询、归还，还是做项目推荐。")

    # 初始化会话
    if "ai_messages" not in st.session_state:
        st.session_state.ai_messages = []
    if "ai_step" not in st.session_state:
        st.session_state.ai_step = "input"
    if "ai_analysis" not in st.session_state:
        st.session_state.ai_analysis = None

    # LLM 配置状态
    config = get_config_status()
    if not config["has_key"]:
        st.warning("未配置 LLM API Key，将使用离线规则（功能有限）。建议在下方展开「高级设置」配置 Key。")

    # 显示历史消息
    for msg in st.session_state.ai_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Step: 显示分析结果
    if st.session_state.ai_step == "showing_result" and st.session_state.ai_analysis:
        analysis = st.session_state.ai_analysis
        intent = analysis.get("intent", "unknown")

        with st.chat_message("assistant"):
            if intent == "unknown":
                st.warning("抱歉，我没太理解你的意图。能换个说法试试吗？")
                st.caption(f"分析: {analysis.get('reasoning', '')}")
                if st.button("好的，我重新说"):
                    st.session_state.ai_step = "input"
                    st.session_state.ai_analysis = None
                    st.rerun()
            else:
                intent_labels = {"inbound": "入库", "outbound": "出库", "search": "查询", "return": "归还", "recommend": "项目推荐"}
                label = intent_labels.get(intent, intent)
                confidence = analysis.get("confidence", "low")
                conf_emoji = {"high": "?", "medium": "?", "low": "?"}.get(confidence, "?")

                st.markdown(f"**{conf_emoji} 我理解你想「{label}」**")
                st.caption(analysis.get("reasoning", ""))

                if analysis.get("name"):
                    st.write(f"物料名称：**{analysis['name']}**")
                if analysis.get("description") and analysis["description"] != analysis.get("user_input", ""):
                    st.caption(f"描述：{analysis['description']}")
                if analysis.get("quantity", 1) > 1:
                    st.write(f"数量：**{analysis['quantity']}**")
                if analysis.get("user_phone"):
                    st.write(f"操作人：{analysis['user_phone']}")
                if intent in ("outbound", "search") and analysis.get("keyword"):
                    st.caption(f"搜索关键词：{analysis['keyword']}")

                # 操作按钮
                if intent == "inbound":
                    if st.button("开始智能入库", type="primary"):
                        st.session_state.ai_step = "confirm_inbound"
                        st.rerun()
                elif intent == "search":
                    if st.button("查询", type="primary"):
                        st.session_state.ai_step = "exec_search"
                        st.rerun()
                elif intent == "return":
                    if st.button("查询待归还", type="primary"):
                        st.session_state.ai_step = "exec_return"
                        st.rerun()
                elif intent == "outbound":
                    if st.button("搜索匹配物料", type="primary"):
                        st.session_state.ai_step = "exec_outbound_list"
                        st.rerun()
                elif intent == "recommend":
                    if st.button("生成物料清单", type="primary"):
                        st.session_state.ai_step = "exec_recommend"
                        _reset_ai_rec_state()
                        st.rerun()

                if st.button("不对，我重新说"):
                    st.session_state.ai_step = "input"
                    st.session_state.ai_analysis = None
                    st.rerun()

    # Step: 确认入库
    elif st.session_state.ai_step == "confirm_inbound" and st.session_state.ai_analysis:
        analysis = st.session_state.ai_analysis

        # 首次进入时调用 infer_material_info 获取详细分类
        if "ai_infer_result" not in st.session_state or st.session_state.ai_infer_result is None:
            with st.spinner("AI 正在推断分类和位置..."):
                use_fake = st.session_state.get("use_fake_ai", False) or not config["has_key"]
                infer_result = infer_material_info(
                    name=analysis.get("name", ""),
                    description=analysis.get("description", ""),
                    use_fake=use_fake
                )
            st.session_state.ai_infer_result = infer_result

        infer = st.session_state.ai_infer_result

        if not infer.get("success"):
            st.error(f"AI 推断失败: {infer.get('error', '')}")
            st.info("请切换到「入库」页面手动操作。")
            if st.button("返回对话"):
                st.session_state.ai_step = "input"
                st.session_state.ai_analysis = None
                st.session_state.ai_infer_result = None
                st.rerun()
        else:
            st.subheader("确认入库信息")
            st.caption(f"已推断分类: **{infer['category']}** → **{infer['sub_category']}**")

            col1, col2 = st.columns(2)
            with col1:
                ai_name = st.text_input("物料名称", value=infer.get("name", analysis.get("name", "")))
                cat_index = CATEGORY_NAMES.index(infer["category"]) if infer["category"] in CATEGORY_NAMES else 0
                ai_category = st.selectbox("大类", CATEGORY_NAMES, index=cat_index)
                subs = get_category_subs(ai_category)
                sub_index = subs.index(infer["sub_category"]) if infer["sub_category"] in subs else 0
                ai_sub = st.selectbox("子类", subs, index=sub_index)
            with col2:
                ai_model = st.text_input("型号", value=infer.get("model", ""))
                ai_is_cons = st.checkbox("耗材", value=infer.get("is_consumable", False))
                ai_qty = st.number_input("数量", min_value=1, value=analysis.get("quantity", 1), step=1)
                ai_loc = st.text_input("存放位置（AI 推荐）", value=infer.get("location", ""))

            conn = get_db()
            try:
                all_tags = [r["name"] for r in conn.execute("SELECT name FROM tags ORDER BY name").fetchall()]
            finally:
                conn.close()
            default_tags = [t for t in infer.get("tags", []) if t in all_tags]
            ai_tags = st.multiselect("标签", all_tags, default=default_tags)

            c1, c2, c3 = st.columns([1, 1, 3])
            if c1.button("确认入库", type="primary"):
                result = add_material(
                    name=ai_name.strip(),
                    category=ai_category,
                    sub_category=ai_sub,
                    model=ai_model.strip(),
                    is_consumable=ai_is_cons,
                    quantity=ai_qty,
                    location=ai_loc.strip(),
                    tags=ai_tags
                )
                st.session_state.ai_messages.append({"role": "assistant", "content": result})
                st.session_state.ai_step = "input"
                st.session_state.ai_analysis = None
                st.session_state.ai_infer_result = None
                st.rerun()
            if c2.button("取消"):
                st.session_state.ai_step = "input"
                st.session_state.ai_analysis = None
                st.session_state.ai_infer_result = None
                st.rerun()

    # Step: 执行查询
    elif st.session_state.ai_step == "exec_search" and st.session_state.ai_analysis:
        analysis = st.session_state.ai_analysis
        keyword = analysis.get("keyword", "") or analysis.get("name", "")

        with st.chat_message("assistant"):
            st.markdown(f"正在搜索与 **{keyword}** 相关的物料...")

            # 1. 按名称/类别/型号搜索
            by_name = search_materials(keyword=keyword)
            # 2. 按标签搜索
            by_tag = search_materials(tag=keyword)

            if "没有找到" in by_name and "没有找到" in by_tag:
                st.warning("没有找到匹配的物料。试试换个说法？")
            else:
                if "没有找到" not in by_name:
                    st.text(by_name)
                if "没有找到" not in by_tag:
                    st.divider()
                    st.caption("以下是通过标签匹配的结果：")
                    st.text(by_tag)

        if st.button("继续对话"):
            st.session_state.ai_step = "input"
            st.session_state.ai_analysis = None
            st.rerun()

    # Step: 执行归还查询
    elif st.session_state.ai_step == "exec_return" and st.session_state.ai_analysis:
        analysis = st.session_state.ai_analysis
        phone = analysis.get("user_phone", "")
        with st.chat_message("assistant"):
            if phone:
                result = get_borrow_records(user_phone=phone, only_active=True)
                st.text(result)
            else:
                st.info("请提供手机号以查询待归还物料。例如：「138xxxx 要归还一块开发板」")
        if st.button("继续对话"):
            st.session_state.ai_step = "input"
            st.session_state.ai_analysis = None
            st.rerun()

    # Step: 出库 — 搜索物料列表（批量）
    elif st.session_state.ai_step == "exec_outbound_list" and st.session_state.ai_analysis:
        analysis = st.session_state.ai_analysis
        keyword = analysis.get("keyword", "") or analysis.get("name", "")

        # 复用结构化搜索：名称/类别/型号 + 标签，按 id 去重
        matched = {}
        for r in search_material_rows(keyword=keyword, only_available=True) + \
                search_material_rows(tag=keyword, only_available=True):
            matched[r["id"]] = r

        # 同名非耗材合并、耗材独立，得到可批量出库的条目
        items = _group_search_rows(list(matched.values()))

        if not items:
            with st.chat_message("assistant"):
                st.warning(f"未找到与「{keyword}」匹配的可出库物料，请检查库存或换个说法。")
            if st.button("返回对话"):
                st.session_state.ai_step = "input"
                st.session_state.ai_analysis = None
                st.rerun()
        else:
            with st.chat_message("assistant"):
                st.markdown(f"找到 **{len(items)}** 类与「{keyword}」匹配的物料，可批量选择：")

            options = {}
            for idx, it in enumerate(items):
                type_label = "耗材" if it["is_consumable"] else "非耗材"
                loc = it["location"] or "未指定"
                label = (f"{it['name']} | {it['category']}>{it['sub_category']} "
                         f"| {type_label} | 库存:{it['available_qty']} | {loc}")
                options[label] = idx

            selected = st.multiselect("选择要出库的物料", list(options.keys()),
                                      key="ai_outbound_select")
            st.caption("非耗材同名已合并显示，出库时按条逐件处理；耗材可一次按量出库。")

            chosen_qty = {}
            for label in selected:
                it = items[options[label]]
                chosen_qty[options[label]] = int(st.number_input(
                    f"{label} — 出库数量",
                    min_value=1, max_value=it["available_qty"], value=1, step=1,
                    key=f"ai_outbound_qty_{options[label]}"
                ))

            col1, col2 = st.columns(2)
            with col1:
                mode = st.radio("出库方式", ["借出（需归还）", "领用（永久出库）"],
                                key="ai_outbound_mode")
            with col2:
                phone = st.text_input("操作人手机号", value=analysis.get("user_phone", ""),
                                      placeholder="13800000001", key="ai_outbound_phone")

            if st.button("确认出库", type="primary"):
                if not phone.strip() or not phone.strip().isdigit() or len(phone.strip()) != 11:
                    st.toast("请输入有效的 11 位手机号", icon=":material/error:")
                elif not selected:
                    st.toast("请选择要出库的物料", icon=":material/error:")
                else:
                    mode_val = "borrow" if "借出" in mode else "consume"
                    report = []
                    for label in selected:
                        it = items[options[label]]
                        need = chosen_qty[options[label]]
                        taken = 0
                        for m in it["matched"]:
                            if m["quantity"] <= 0:
                                continue
                            want = min(need - taken, m["quantity"])
                            r = checkout(m["id"], phone.strip(), mode_val, quantity=want)
                            if "成功" in r:
                                taken += want
                                m["quantity"] -= want
                            elif not m["is_consumable"] and want > 1:
                                r = checkout(m["id"], phone.strip(), mode_val, quantity=1)
                                if "成功" in r:
                                    taken += 1
                                    m["quantity"] -= 1
                            if taken >= need:
                                break
                        report.append(f"{it['name']}：出库 {taken}/{need} 件")
                    st.session_state.ai_messages.append(
                        {"role": "assistant",
                         "content": "批量出库完成：\n" + "\n".join(report)}
                    )
                    st.session_state.ai_step = "input"
                    st.session_state.ai_analysis = None
                    st.toast("批量出库完成", icon=":material/check:")
                    st.rerun()

            if st.button("取消"):
                st.session_state.ai_step = "input"
                st.session_state.ai_analysis = None
                st.rerun()

    # Step: 执行项目推荐
    elif st.session_state.ai_step == "exec_recommend" and st.session_state.ai_analysis:
        analysis = st.session_state.ai_analysis
        # 优先用原始输入，其次用 LLM 提取的描述
        desc = (analysis.get("user_input")
                or analysis.get("description")
                or analysis.get("name", ""))

        # 首次进入该步骤时调用一次分析，之后用会话缓存渲染（避免每次交互都重跑 LLM）
        if st.session_state.get("ai_rec_result") is None:
            with st.spinner("AI 正在推理物料清单并对照库存..."):
                use_fake = st.session_state.get("use_fake_ai", False) or not config["has_key"]
                try:
                    result = analyze_project(desc, use_fake=use_fake)
                except Exception as e:
                    result = {"success": False, "error": f"推荐失败：{e}"}
            st.session_state.ai_rec_result = result

        result = st.session_state.ai_rec_result

        with st.chat_message("assistant"):
            if not result.get("success"):
                st.error(result.get("error", "分析失败，请换个说法试试。"))
            else:
                s = result["summary"]
                st.markdown(
                    f"项目：**{result.get('project_name') or '（未命名项目）'}**　|　"
                    f"? 可满足 {s['ok']} 项　?? 部分满足 {s['partial']} 项　? 缺货 {s['missing']} 项"
                )
                if result.get("llm_error"):
                    st.info(f"LLM 调用失败，已降级为离线规则（{result['llm_error'][:80]}）")
                if result.get("dropped"):
                    st.caption("；".join(result["dropped"]))

                # 明细清单
                status_emoji = {"ok": "?", "partial": "??", "missing": "?"}
                status_label = {"ok": "有货", "partial": "部分满足", "missing": "缺货"}
                for it in result["items"]:
                    optional = "（可选）" if it["necessity"] == "optional" else ""
                    title = (f"{status_emoji[it['status']]} {status_label[it['status']]}  "
                             f"**{it['name']}**{optional} — {it['category']}>{it['sub_category']} "
                             f"| 需 {it['quantity']} 件 | 库存 {it['available_qty']}")
                    with st.expander(title, expanded=(it["status"] != "ok")):
                        if it["note"]:
                            st.caption(f"说明：{it['note']}")
                        if it["matched"]:
                            for m in it["matched"][:5]:
                                st.write(f"· `{m['id']}` {m['name']} | 库存 {m['quantity']} | {m['location'] or '未指定位置'}")
                        if it["shortage"]:
                            st.warning(f"库存不足，还缺 {it['shortage']} 件")
                        if it["alternatives"]:
                            st.caption("? 同类替代：")
                            for a in it["alternatives"]:
                                st.write(f"· `{a['id']}` {a['name']}（{a['sub_category']}）库存 {a['quantity']}")
                        elif it["shortage"]:
                            st.caption("? 无同类替代品，建议采购")

        # 批量出库（放在对话气泡外，操作更顺手）
        if result.get("success"):
            ok_items = [it for it in result["items"] if it["status"] in ("ok", "partial")]
            if ok_items:
                st.divider()
                st.subheader("批量出库")
                options = {}
                default_selected = []
                for idx, it in enumerate(ok_items):
                    label = f"{it['name']}（{it['category']}>{it['sub_category']}）"
                    options[label] = idx
                    # 库存充足的项默认勾选；部分满足的项会出完该类剩余库存，默认不勾选
                    if it["status"] == "ok":
                        default_selected.append(label)
                st.caption("已自动勾选库存充足的项；?? 部分满足的项默认不勾选"
                           "（勾选后会把该类剩余库存全部出完），需要时手动勾选。")
                selected = st.multiselect("选择要出库的物料", list(options.keys()),
                                          default=default_selected, key="ai_rec_select")

                # 每个勾选项可微调出库数量（默认 = min(需求, 库存)）
                chosen_qty = {}
                for label in selected:
                    it = ok_items[options[label]]
                    cap = it["available_qty"]
                    chosen_qty[options[label]] = int(st.number_input(
                        f"{label} — 出库数量",
                        min_value=1, max_value=cap,
                        value=min(it["quantity"], cap), step=1,
                        key=f"ai_rec_qty_{options[label]}"
                    ))

                col1, col2 = st.columns(2)
                with col1:
                    mode_rec = st.radio("出库方式", ["借出（需归还）", "领用（永久出库）"], key="ai_rec_mode")
                with col2:
                    phone_rec = st.text_input("操作人手机号", key="ai_rec_phone",
                                              placeholder="如：13800000001")

                if st.button("确认批量出库", type="primary"):
                    if not phone_rec.strip() or not phone_rec.strip().isdigit() or len(phone_rec.strip()) != 11:
                        st.toast("请输入有效的 11 位手机号", icon=":material/error:")
                    elif not selected:
                        st.toast("请选择要出库的物料", icon=":material/error:")
                    else:
                        mode_val = "borrow" if "借出" in mode_rec else "consume"
                        report = []
                        for label in selected:
                            it = ok_items[options[label]]
                            need = chosen_qty[options[label]]
                            taken = 0
                            for m in it["matched"]:
                                if m["quantity"] <= 0:
                                    continue
                                want = min(need - taken, m["quantity"])
                                # 耗材合并在一行，一次按量出库；非耗材每行 1 件
                                r = checkout(m["id"], phone_rec.strip(), mode_val, quantity=want)
                                if "成功" in r:
                                    taken += want
                                    m["quantity"] -= want
                                elif not m["is_consumable"] and want > 1:
                                    # 逐条兜底：同批非耗材只按 1 件重试（理论上到不了这里）
                                    r = checkout(m["id"], phone_rec.strip(), mode_val, quantity=1)
                                    if "成功" in r:
                                        taken += 1
                                        m["quantity"] -= 1
                                if taken >= need:
                                    break
                            report.append(f"{it['name']}：出库 {taken}/{need} 件")
                        st.session_state.ai_messages.append(
                            {"role": "assistant",
                             "content": "批量出库完成：\n" + "\n".join(report)}
                        )
                        st.session_state.ai_step = "input"
                        st.session_state.ai_analysis = None
                        _reset_ai_rec_state()
                        st.toast("批量出库完成", icon=":material/check:")
                        st.rerun()

        if st.button("继续对话"):
            st.session_state.ai_step = "input"
            st.session_state.ai_analysis = None
            st.session_state.ai_rec_result = None
            st.rerun()

    # Step: 输入（默认）
    else:
        pass  # chat_input 在下面

    # 输入框
    user_input = st.chat_input("说说你想做什么...")
    if user_input:
        st.session_state.ai_messages.append({"role": "user", "content": user_input})

        with st.spinner("AI 正在分析..."):
            use_fake = st.session_state.get("use_fake_ai", False) or not config["has_key"]
            try:
                if use_fake:
                    analysis = classify_intent_fake(user_input)
                else:
                    analysis = classify_intent(user_input)
            except Exception as e:
                analysis = classify_intent_fake(user_input)
                if "未配置" not in str(e):
                    analysis["reasoning"] = f"(LLM 调用失败，已降级为离线规则: {e})"

        # 添加 AI 回复到消息
        intent = analysis.get("intent", "unknown")
        name = analysis.get("name", "")
        if intent == "unknown":
            ai_content = "抱歉，我没太理解你的意图。能换个说法试试吗？"
        elif intent == "inbound":
            ai_content = f"我理解你想**入库**「{name or '未知物料'}」"
            if analysis.get("quantity", 1) > 1:
                ai_content += f"，数量约 {analysis['quantity']} 个"
            ai_content += "。"
        elif intent == "search":
            kw = analysis.get("keyword", "") or name
            ai_content = f"我理解你想**查询**「{kw}」的库存情况。"
        elif intent == "outbound":
            kw = analysis.get("keyword", "") or name
            ai_content = f"我理解你想**出库**「{name or kw}」，正在为您匹配库存..."
        elif intent == "return":
            ai_content = f"我理解你想**归还**物料。"
        elif intent == "recommend":
            ai_content = f"我理解你想**规划一个项目**「{name or '（见描述）'}」，让我为你推理所需物料清单..."
        else:
            ai_content = "收到，让我想想..."

        st.session_state.ai_messages.append({"role": "assistant", "content": ai_content})
        if intent == "search":
            st.session_state.ai_step = "exec_search"
        elif intent == "recommend":
            st.session_state.ai_step = "exec_recommend"
            _reset_ai_rec_state()
        else:
            st.session_state.ai_step = "showing_result"
        analysis["user_input"] = user_input
        st.session_state.ai_analysis = analysis
        st.rerun()

    # 高级设置
    with st.expander("高级设置"):
        st.checkbox("使用离线规则", key="use_fake_ai",
                    help="勾选后使用内置关键词规则，无需 LLM API Key。")

        st.divider()
        st.caption("LLM API 配置")
        if config["has_key"]:
            st.success(f"已配置 | {config['base_url']} | {config['model']} | Key: {config['key_prefix']}")
        else:
            st.warning("未配置 LLM API Key")

        new_key = st.text_input("设置 API Key（保存到本地）",
                                type="password",
                                placeholder="sk-xxx",
                                help="支持 DeepSeek、通义千问等 OpenAI 兼容 API。\n\nKey 会保存到本地文件（已排除在 git 之外，不会提交）。")
        if st.button("应用并保存"):
            if new_key.strip():
                llm_configure(api_key=new_key.strip())
                st.toast("API Key 已保存", icon=":material/check:")
                st.rerun()

# ==================== 入库 ====================
elif page == "入库":
    st.header("物料入库")

    if st.session_state.get("add_step") == "confirm":
        d = st.session_state.get("add_info", {})
        st.warning("确认入库以下物料？")
        cols = st.columns(2)
        cols[0].write(f"名称：**{d['name']}**")
        cols[1].write(f"大类：**{d['category']}**")
        cols[0].write(f"子类：**{d['sub_category'] or '未指定'}**")
        cols[1].write(f"型号：**{d['model'] or '未指定'}**")
        cols[0].write(f"数量：**{d['quantity']}**")
        cols[1].write(f"类型：**{'耗材' if d['is_consumable'] else '非耗材（每件独立编号）'}**")
        if d.get("location"):
            cols[0].write(f"位置：**{d['location']}**")
        if d.get("tags"):
            cols[1].write(f"标签：**{', '.join(d['tags'])}**")

        c1, c2, c3 = st.columns([1, 1, 3])
        if c1.button("确认入库", type="primary"):
            result = add_material(**d)
            if "成功" in result:
                st.toast("入库成功", icon=":material/check:")
            else:
                st.toast(result, icon=":material/error:")
            st.session_state.add_step = None
            st.session_state.add_info = None
            st.rerun()
        if c2.button("取消"):
            st.session_state.add_step = None
            st.session_state.add_info = None
            st.rerun()

    else:
        # 标签数据提前加载（在所有行之前只查一次）
        conn = get_db()
        try:
            all_tags = [r["name"] for r in conn.execute("SELECT name FROM tags ORDER BY name").fetchall()]
        finally:
            conn.close()

        # ---- 第 1 行：物料名称 | 存放位置 ----
        r1_left, r1_right = st.columns(2)
        with r1_left:
            name = st.text_input("物料名称", placeholder="如：STM32F407 开发板")
        with r1_right:
            location = st.text_input("存放位置", placeholder="如：柜A-1")

        # ---- 第 2 行：大类 | 子类 ----
        r2_left, r2_right = st.columns(2)
        with r2_left:
            category = st.selectbox("大类", CATEGORY_NAMES)
        with r2_right:
            sub_category = st.selectbox("子类", get_category_subs(category))

        # ---- 第 3 行：型号 | 数量 ----
        r3_left, r3_right = st.columns(2)
        with r3_left:
            model = st.text_input("型号", placeholder="如：STM32F407")
        with r3_right:
            quantity = st.number_input("数量", min_value=1, value=1, step=1,
                                       help="非耗材每件独立编号，耗材合并数量")

        # ---- 第 4 行：标签（可选） | 新增标签 ----
        r4_left, r4_right = st.columns(2)
        with r4_left:
            selected_tags = st.multiselect("标签（可选）", all_tags,
                                           help="选择已有标签或下方输入新标签名，入库时自动关联"
                                                   "。标签描述在「标签管理」页面查看。")
        with r4_right:
            new_tags = st.text_input("新增标签（逗号分隔）",
                                     placeholder="如：IoT开发板, 教学常用",
                                     help="输入新标签名，入库时自动创建。标签描述可在「标签管理」页补充。")

        # ---- 元选项：是否为耗材（放在表单末尾，提交按钮之前，不打断对齐网格） ----
        is_consumable = st.checkbox(
            "标记为耗材",
            value=False,
            help="勾选后按总量管理（如焊锡丝、热缩管）；不勾选则每件物料独立编号。"
        )

        if st.button("入库确认", type="primary", use_container_width=True):
            if not name.strip():
                st.toast("请输入物料名称", icon=":material/error:")
            else:
                # 合并已有标签选择和新标签
                all_selected = list(selected_tags)
                if new_tags.strip():
                    for t in new_tags.split(","):
                        t = t.strip()
                        if t and t not in all_selected:
                            # 自动创建新标签（无描述）
                            conn = get_db()
                            try:
                                conn.execute("INSERT OR IGNORE INTO tags (name, description) VALUES (?, '')", (t,))
                                conn.commit()
                            finally:
                                conn.close()
                            all_selected.append(t)

                st.session_state.add_step = "confirm"
                st.session_state.add_info = {
                    "name": name.strip(),
                    "category": category,
                    "sub_category": sub_category,
                    "model": model.strip(),
                    "is_consumable": is_consumable,
                    "quantity": quantity,
                    "location": location.strip(),
                    "tags": all_selected
                }
                st.rerun()

# ==================== 出库 ====================
elif page == "出库":
    st.header("物料出库")

    if st.session_state.get("checkout_step") == "confirm":
        d = st.session_state.get("checkout_info", {})
        st.warning(f"确认{d['mode_label']}以下物料？")
        st.write(f"物料：**{d['name']}**（{d['id']}）")
        st.write(f"操作人：**{d['phone']}**")
        if d.get("quantity", 1) > 1:
            st.write(f"数量：**{d['quantity']}**")

        c1, c2, c3 = st.columns([1, 1, 3])
        if c1.button("确认", type="primary"):
            result = checkout(d["id"], d["phone"], d["mode"], quantity=d.get("quantity", 1))
            if "成功" in result:
                st.toast(f"{d['mode_label']}成功", icon=":material/check:")
            else:
                st.toast(result, icon=":material/error:")
            st.session_state.checkout_step = None
            st.session_state.checkout_info = None
            st.rerun()
        if c2.button("取消"):
            st.session_state.checkout_step = None
            st.session_state.checkout_info = None
            st.rerun()

    else:
        conn = get_db()
        try:
            materials = conn.execute(
                "SELECT id, name, category, quantity, is_consumable FROM materials WHERE quantity>0 ORDER BY category, name"
            ).fetchall()
        finally:
            conn.close()

        if not materials:
            st.info("库存为空，请先入库。")
        else:
            options = {f"[{m['id']}] {m['name']} ({m['category']}, 库存:{m['quantity']})": m for m in materials}
            selected_label = st.selectbox("选择物料", list(options.keys()))
            selected = options[selected_label]

            col1, col2 = st.columns(2)
            with col1:
                mode = st.radio("出库方式", ["借出（需归还）", "领用（永久出库）"],
                               index=0 if not selected["is_consumable"] else 1)
            with col2:
                phone = st.text_input("操作人手机号", placeholder="如：13800000001")

            # 耗材合并在一行，可一次出多件；非耗材每件独立编号，只能 1 件
            # key 绑定物料 ID：切换物料时输入框自动重置，避免旧值超出新物料库存
            qty = 1
            if selected["is_consumable"]:
                qty = int(st.number_input("出库数量", min_value=1,
                                         max_value=selected["quantity"],
                                         value=1, step=1,
                                         key=f"co_qty_{selected['id']}"))

            if st.button("出库", type="primary", use_container_width=True):
                if not phone.strip():
                    st.toast("请输入手机号", icon=":material/error:")
                else:
                    mode_label = "借出" if "借出" in mode else "领用"
                    st.session_state.checkout_step = "confirm"
                    st.session_state.checkout_info = {
                        "id": selected["id"],
                        "name": selected["name"],
                        "phone": phone.strip(),
                        "mode": "borrow" if "借出" in mode else "consume",
                        "mode_label": mode_label,
                        "quantity": qty
                    }
                    st.rerun()

# ==================== 归还 ====================
elif page == "归还":
    st.header("物料归还")

    if st.session_state.get("return_step") == "confirm":
        d = st.session_state.get("return_info", {})
        st.warning("确认归还以下物料？")
        st.write(f"物料：**{d['name']}**")
        st.write(f"借出时间：{d['borrowed_at']}")
        st.write(f"归还编号：{d['id']}")

        c1, c2, c3 = st.columns([1, 1, 3])
        if c1.button("确认归还", type="primary"):
            result = return_item(str(d["id"]))
            if "成功" in result:
                st.toast(f"已归还：{d['name']}", icon=":material/check:")
            else:
                st.toast(result, icon=":material/error:")
            st.session_state.return_step = None
            st.session_state.return_info = None
            st.rerun()
        if c2.button("取消"):
            st.session_state.return_step = None
            st.session_state.return_info = None
            st.rerun()

    else:
        phone = st.text_input("输入手机号查询借出记录", placeholder="如：13800000001")

        if phone.strip():
            conn = get_db()
            try:
                rows = conn.execute(
                    """SELECT br.id, br.material_id, m.name, br.quantity, br.borrowed_at
                       FROM borrow_records br
                       LEFT JOIN materials m ON br.material_id = m.id
                       WHERE br.user_phone=? AND br.status='active'
                       ORDER BY br.borrowed_at DESC""",
                    (phone.strip(),)
                ).fetchall()
            finally:
                conn.close()

            if not rows:
                st.info(f"手机号 {phone.strip()} 没有待归还的物料。")
            else:
                st.write(f"共 {len(rows)} 件待归还：")
                for row in rows:
                    mat_name = row["name"] or row["material_id"]
                    c1, c2 = st.columns([5, 1])
                    with c1:
                        st.write(f"**{mat_name}**  |  归还编号 `{row['id']}`  |  "
                                 f"借出 {row['quantity']} 件  |  {row['borrowed_at']}")
                    with c2:
                        if st.button("归还", key=f"ret_{row['id']}", type="primary"):
                            st.session_state.return_step = "confirm"
                            st.session_state.return_info = {
                                "id": row["id"],
                                "name": mat_name,
                                "borrowed_at": row["borrowed_at"]
                            }
                            st.rerun()
                    st.divider()

# ==================== 记录查询 ====================
elif page == "记录查询":
    st.header("出库记录查询")

    # 头部一行：记录类型 + 筛选开关（把「仅显示借出中」挪到顶部和类型同一行）
    rec_head_left, rec_head_right = st.columns([3, 1])
    with rec_head_left:
        rec_view = st.radio("记录类型", ["借还记录", "领用记录"], horizontal=True)
    with rec_head_right:
        only_active = False
        if rec_view == "借还记录":
            only_active = st.checkbox("仅显示借出中", value=False)

    if rec_view == "借还记录":
        # 手机号输入框：全宽，与领用记录样式一致
        filter_phone = st.text_input("按手机号筛选", placeholder="留空查看全部",
                                     key="rec_filter_phone_borrow")

        result = get_borrow_records(
            user_phone=filter_phone.strip(),
            only_active=only_active
        )
        if "没有找到" in result:
            st.info(result)
        else:
            st.text(result)
    else:
        # 领用记录（永久出库，不归还）—— 手机号输入框保持全宽样式
        filter_phone = st.text_input("按手机号筛选", placeholder="留空查看全部",
                                     key="rec_filter_phone_consume")
        conn = get_db()
        try:
            query = """
                SELECT o.id, o.material_id, m.name AS material_name,
                       o.quantity, o.user_phone, o.created_at
                FROM outbound_records o
                LEFT JOIN materials m ON o.material_id = m.id
                WHERE o.mode = 'consume'
            """
            params = []
            if filter_phone.strip():
                query += " AND o.user_phone = ?"
                params.append(filter_phone.strip())
            query += " ORDER BY o.created_at DESC"
            rows = conn.execute(query, params).fetchall()
        finally:
            conn.close()

        if not rows:
            st.info("没有找到匹配的领用记录。")
        else:
            lines = []
            for r in rows:
                lines.append(
                    f"[{r['id']}] {r['material_name'] or r['material_id']} "
                    f"| 领用人：{r['user_phone']} "
                    f"| 数量：{r['quantity']} 件 "
                    f"| 时间：{r['created_at']}"
                )
            st.text(f"共 {len(rows)} 条记录：\n" + "\n".join(lines))

# ==================== 标签管理 ====================
elif page == "标签管理":
    st.header("标签管理")
    st.caption("标签用于帮助智能体理解物料特性。标签名是产品系列，描述补充说明该物料能做什么。")

    # 显示所有标签
    conn = get_db()
    try:
        all_tags = conn.execute(
            "SELECT t.name, t.description, COUNT(mt.material_id) as item_count "
            "FROM tags t LEFT JOIN material_tags mt ON t.name = mt.tag_name "
            "GROUP BY t.name ORDER BY t.name"
        ).fetchall()
    finally:
        conn.close()

    st.subheader(f"标签库（共 {len(all_tags)} 个）")

    for t in all_tags:
        c1, c2 = st.columns([3, 1])
        with c1:
            st.markdown(f"**{t['name']}**{'  (' + str(t['item_count']) + ' 件物料)' if t['item_count'] else ''}")
            if t["description"]:
                st.caption(t["description"])
            else:
                st.caption("? 暂无描述")
        with c2:
            if st.button("编辑描述", key=f"edit_{t['name']}"):
                st.session_state.edit_tag = t["name"]
                st.session_state.edit_desc = t["description"]
                st.rerun()
        st.divider()

    # 编辑标签描述
    if st.session_state.get("edit_tag"):
        st.subheader(f"编辑标签描述：{st.session_state.edit_tag}")
        new_desc = st.text_area("描述", value=st.session_state.get("edit_desc", ""),
                                placeholder="描述该标签对应的物料特性，供 LLM 检索使用...")
        c1, c2, c3 = st.columns([1, 1, 3])
        if c1.button("保存"):
            conn = get_db()
            try:
                conn.execute("UPDATE tags SET description=? WHERE name=?", (new_desc, st.session_state.edit_tag))
                conn.commit()
            finally:
                conn.close()
            st.toast("描述已更新", icon=":material/check:")
            st.session_state.edit_tag = None
            st.session_state.edit_desc = None
            st.rerun()
        if c2.button("取消"):
            st.session_state.edit_tag = None
            st.session_state.edit_desc = None
            st.rerun()
