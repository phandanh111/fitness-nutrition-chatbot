from typing import List, Tuple

RAW_CITY_ALIAS_PAIRS: List[Tuple[str, List[str]]] = [
    ("Hồ Chí Minh", ["hồ chí minh", "ho chi minh", "tp.hcm", "tphcm", "tp hcm", "hcm", "sài gòn", "sai gon"]),
    ("Đà Nẵng", ["đà nẵng", "da nang", "dn"]),
    ("Cần Thơ", ["cần thơ", "can tho", "ct", "ninh kiều", "ninh kieu"]),
    ("Đồng Nai", ["đồng nai", "dong nai", "biên hòa", "bien hoa", "biên hoà"]),
    ("Bà Rịa Vũng Tàu", ["bà rịa vũng tàu", "ba ria vung tau", "vũng tàu", "vung tau", "brvt"]),
    ("An Giang", ["an giang", "long xuyên", "long xuyen"]),
]

RAW_DISTRICT_ALIAS_PAIRS: List[Tuple[str, List[str]]] = [
    ("Quận 1", ["quan 1", "quận 1", "district 1"]),
    ("Quận 2", ["quan 2", "quận 2", "district 2"]),
    ("Quận 3", ["quan 3", "quận 3", "district 3"]),
    ("Quận 4", ["quan 4", "quận 4", "district 4"]),
    ("Quận 5", ["quan 5", "quận 5", "district 5"]),
    ("Quận 6", ["quan 6", "quận 6", "district 6"]),
    ("Quận 7", ["quan 7", "quận 7", "district 7"]),
    ("Quận 8", ["quan 8", "quận 8", "district 8"]),
    ("Quận 9", ["quan 9", "quận 9", "district 9"]),
    ("Quận 10", ["quan 10", "quận 10", "district 10"]),
    ("Quận 11", ["quan 11", "quận 11", "district 11"]),
    ("Quận 12", ["quan 12", "quận 12", "district 12"]),
    (
        "Bình Thạnh",
        ["binh thanh", "bình thạnh", "quan binh thanh", "quận bình thạnh", "district binh thanh"],
    ),
    (
        "Tân Bình",
        ["tan binh", "tân bình", "quan tan binh", "quận tân bình", "district tan binh"],
    ),
    (
        "Phú Nhuận",
        ["phu nhuan", "phú nhuận", "quan phu nhuan", "quận phú nhuận", "district phu nhuan"],
    ),
    (
        "Gò Vấp",
        ["go vap", "gò vấp", "quan go vap", "quận gò vấp", "district go vap"],
    ),
    (
        "Tân Phú",
        ["tan phu", "tân phú", "quan tan phu", "quận tân phú", "district tan phu"],
    ),
    (
        "Bình Tân",
        ["binh tan", "bình tân", "quan binh tan", "quận bình tân", "district binh tan"],
    ),
    (
        "Bình Chánh",
        ["binh chanh", "bình chánh", "quan binh chanh", "quận bình chánh", "district binh chanh"],
    ),
    (
        "Nhà Bè",
        ["nha be", "nhà bè", "quan nha be", "quận nhà bè", "district nha be"],
    ),
    (
        "Hóc Môn",
        ["hoc mon", "hóc môn", "quan hoc mon", "quận hóc môn", "district hoc mon"],
    ),
    (
        "Củ Chi",
        ["cu chi", "củ chi", "quan cu chi", "quận củ chi", "district cu chi"],
    ),
    (
        "Hải Châu",
        ["hai chau", "hải châu", "quan hai chau", "quận hải châu", "district hai chau"],
    ),
    (
        "Ninh Kiều",
        ["ninh kieu", "ninh kiều", "quan ninh kieu", "quận ninh kiều", "district ninh kieu"],
    ),
    ("Thành phố Biên Hòa", ["bien hoa", "biên hòa"]),
    ("Thành phố Vũng Tàu", ["vung tau", "vũng tàu"]),
    ("Thành phố Long Xuyên", ["long xuyen", "long xuyên"]),
]

COUNT_KEYWORDS = [
    "bao nhieu",
    "bao nhiêu",
    "co may",
    "có mấy",
    "có bao nhieu",
    "có bao nhiêu",
    "tong cong",
    "tổng cộng",
    "so luong",
    "số lượng",
]

ACTIVE_KEYWORDS = [
    "dang hoat dong",
    "đang hoạt động",
    "mo cua",
    "mở cửa",
    "con hoat dong",
    "còn hoạt động",
]

INACTIVE_KEYWORDS = [
    "tam dong",
    "tạm đóng",
    "tam ngung",
    "tạm ngưng",
    "tam ngưng",
    "da dong",
    "đã đóng",
    "ngung hoat dong",
    "ngừng hoạt động",
]

ADDRESS_KEYWORDS = [
    "dia chi",
    "địa chỉ",
    "o dau",
    "ở đâu",
    "vi tri",
    "vị trí",
    "location",
]

DISTRICT_KEYWORDS = [
    "quan",
    "quận",
    "huyen",
    "huyện",
    "phuong",
    "phường",
    "ward",
]
