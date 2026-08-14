# -*- coding: utf-8 -*-
"""数据模型定义（dataclass）"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Material:
    """物料"""
    id: str
    name: str
    category: str
    category_code: str = ""
    sub_category: str = ""
    sub_category_code: str = ""
    model: str = ""
    is_consumable: bool = False
    quantity: int = 0
    location: str = ""
    created_at: str = ""


@dataclass
class Tag:
    """标签（含描述，供 LLM 语义检索用）"""
    name: str
    description: str = ""


@dataclass
class User:
    """用户（手机号为主键）"""
    phone: str
    name: str = ""


@dataclass
class OutboundRecord:
    """出库记录（含借出和领用）"""
    id: int
    material_id: str
    user_phone: str
    mode: str  # "borrow" 或 "consume"
    quantity: int = 1
    created_at: str = ""


@dataclass
class BorrowRecord:
    """借还记录（仅 borrow 模式出库时创建）"""
    id: int
    material_id: str
    user_phone: str
    borrowed_at: str = ""
    returned_at: Optional[str] = None
    status: str = "active"  # "active" 或 "returned"
