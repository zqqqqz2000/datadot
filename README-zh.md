# DataDot (DD) 🔍

![开发中](https://img.shields.io/badge/状态-开发中-yellow)

DataDot (DD) 是一个用于简化数据访问的Python库。它提供了一种链式调用方式来安全地访问嵌套的数据结构，无需繁琐的空值检查。

## 主要特性

- 链式调用API
- 安全的属性和索引访问
- 空值安全处理 (使用 `._` 启用)
- 数据结构展开操作
- 友好的错误提示

## 示例

```python
# 假设有以下嵌套数据结构
data = {
    "users": [
        {"name": "张三", "details": {"age": 30, "email": "zhangsan@example.com"}},
        {"name": "李四", "details": {"age": 25, "email": "lisi@example.com"}}
    ]
}

# 使用DD访问数据
from src.dd import dd

# 获取第一个用户的邮箱
email = dd(data).users[0].details.email()
print(email)  # 输出: zhangsan@example.com

# 空值安全处理
missing = dd(data)._.users[3].details.email()
print(missing)  # 输出: None 而不是抛出异常

# 展开操作获取所有用户名
names = dd(data).users[...].name()
print(names)  # 输出: ['张三', '李四']
```

## ✨ 功能特点

- 🔗 **链式API**: 通过点符号轻松导航嵌套数据
- 🛡️ **错误处理**: 带有路径信息的美观错误消息
- 🔒 **空值安全**: 通过 `._` 实现可选的空值安全操作（应用于所有后续操作）
- 🔄 **列表/字典展开**: 使用 `[...]` 处理集合中的所有项目
- ⏳ **惰性求值**: 操作被记录并仅在需要最终值时执行

## 📦 安装

```bash
pip install datadot
```

## 🚀 快速开始

### 🔰 基本用法

```python
from src.dd import dd

# 简单的数据访问
data = {"users": [{"name": "小明", "age": 30}, {"name": "小红", "age": 25}]}
ming_age = dd(data).users[0].age()  # 返回 30

# 使用转换函数
is_adult = dd(data).users[0].age(lambda x: x >= 18)  # 返回 True
```

### 🛡️ 空值安全

```python
# 传统方式 - 会引发 AttributeError 💥
data = {"users": None}
try:
    users = data["users"][0].name
except AttributeError:
    print("访问属性时发生错误")

# 使用 dd - 安全导航 ✅
# 一旦使用 ._ ，所有后续操作自动变为空值安全
result = dd(data)._.users[0].name()  # 不会引发错误，返回 None
```

### 🔄 列表/字典展开

```python
# 获取所有用户名
data = {"users": [{"name": "小明"}, {"name": "小红"}, {"name": "小刚"}]}
names = dd(data).users[...].name()  # 返回 ["小明", "小红", "小刚"]

# 获取字典中的所有值
config = {"server": {"ports": {"http": 80, "https": 443}}}
ports = dd(config).server.ports[...]()  # 返回 [80, 443]
```

### 🔀 功能组合

```python
# 从可能为空的数据中安全获取所有用户年龄
data = {"groups": [{"users": None}, {"users": [{"name": "小明", "age": 30}]}]}
# 不需要重复 ._ ，因为它适用于所有后续操作
ages = dd(data).groups[...]._.users[...].age()  # 返回 [[], [30, 15]]

# 筛选成年用户
adult_names = dd(data).groups[...]._.users[...](
    lambda users_groups: [
        [user["name"] for user in (users or []) if user.get("age", 0) >= 18]
        for users in users_groups
    ]
)  # 返回 [[], ["小明"]]
```

### ⚠️ 错误处理

```python
# 访问不存在的键时提供描述性错误
data = {"users": [{"name": "小明"}]}
try:
    dd(data).users[0].email()
except Exception as e:
    print(e)  # 打印: "Failed to get attribute 'email': 'dict' object has no attribute 'email'
               # at path: dd.users[0].email, value: {'name': '小明'}"
```

## 🧙‍♂️ 高级用法

### 🧮 自定义转换

```python
# 对提取的数据应用转换
data = {"items": [{"price": 10}, {"price": 20}, {"price": 30}]}
total = dd(data).items[...].price(lambda prices: sum(prices))  # 返回 60

# 将所有名称格式化为大写
data = {"users": [{"name": "xiaoming"}, {"name": "xiaohong"}]}
upper_names = dd(data).users[...].name(lambda names: [n.upper() for n in names])
# 返回 ["XIAOMING", "XIAOHONG"]
```

### 🌐 处理API响应

```python
import requests
from src.dd import dd

# 使用单个 ._ 安全地导航API响应，适用于整个链
response = requests.get("https://api.example.com/data").json()
first_tag = dd(response)._.data.items[0].tags[0]()  # 安全获取第一个标签，即使任何部分为None

# 安全处理所有项目
all_prices = dd(response)._.data.items[...].price()  # 获取所有价格，处理空值
```

## 📄 许可证

MIT

