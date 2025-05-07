# DataDot (DD) 🔍

![WIP](https://img.shields.io/badge/Status-WIP-yellow)

[中文文档](README-zh.md) | English

DataDot (DD) is a Python library designed to simplify data access. It provides a chain-style calling method to safely access nested data structures without cumbersome null checks.

## Key Features

- Chain-style API
- Safe attribute and index access
- Null-safe handling (using `._` modifier)
- Data structure expansion operations
- Friendly error messages

## Examples

```python
# Assume we have the following nested data structure
data = {
    "users": [
        {"name": "Zhang San", "details": {"age": 30, "email": "zhangsan@example.com"}},
        {"name": "Li Si", "details": {"age": 25, "email": "lisi@example.com"}}
    ]
}

# Using DD to access data
from dd import dd

# Get the email of the first user
email = dd(data).users[0].details.email()
print(email)  # Output: zhangsan@example.com

# Null-safe handling
missing = dd(data)._.users[3].details.email()
print(missing)  # Output: None instead of raising an exception

# Expansion operation to get all user names
names = dd(data).users[...].name()
print(names)  # Output: ['Zhang San', 'Li Si']
```

## ✨ Features

- 🔗 **Chainable API**: Easy navigation through nested data with dot notation
- 🛡️ **Error Handling**: Beautiful error messages with path information
- 🔒 **Null Safety**: Optional null-safe operations with `._` (applies to all subsequent operations)
- 🔄 **List/Dict Expansion**: Process all items in a collection with `[...]`
- ⏳ **Lazy Evaluation**: Operations are recorded and only executed when the final value is needed

## 📦 Installation

```bash
pip install datadot
```

## 🚀 Quick Start

### 🔰 Basic Usage

```python
from dd import dd

# Simple data access
data = {"users": [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]}
alice_age = dd(data).users[0].age()  # Returns 30

# With conversion function
is_adult = dd(data).users[0].age(lambda x: x >= 18)  # Returns True
```

### 🛡️ Null Safety

```python
# Traditional way - will raise AttributeError 💥
data = {"users": None}
try:
    users = data["users"][0].name
except AttributeError:
    print("Error accessing attribute")

# With dd - safe navigation ✅
# Once ._ is used, all subsequent operations become null-safe automatically
result = dd(data)._.users[0].name()  # Returns None without error
```

### 🔄 List/Dict Expansion

```python
# Get all user names
data = {"users": [{"name": "Alice"}, {"name": "Bob"}, {"name": "Charlie"}]}
names = dd(data).users[...].name()  # Returns ["Alice", "Bob", "Charlie"]

# Get all values from a dictionary
config = {"server": {"ports": {"http": 80, "https": 443}}}
ports = dd(config).server.ports[...]()  # Returns [80, 443]
```

### 🔀 Combining Features

```python
# Safely get all user ages from potentially null data
data = {"groups": [{"users": None}, {"users": [{"name": "Alice", "age": 30}]}]}
# No need to repeat ._ as it applies to all subsequent operations
ages = dd(data).groups[...]._.users[...].age()  # Returns [[], [30, 15]]

# Filter adult users
adult_names = dd(data).groups[...]._.users[...](
    lambda users_groups: [
        [user["name"] for user in (users or []) if user.get("age", 0) >= 18]
        for users in users_groups
    ]
)  # Returns [[], ["Alice"]]
```

### ⚠️ Error Handling

```python
# Accessing a non-existent key with descriptive error
data = {"users": [{"name": "Alice"}]}
try:
    dd(data).users[0].email()
except Exception as e:
    print(e)  # Prints: "Failed to get attribute 'email': 'dict' object has no attribute 'email'
               # at path: dd.users[0].email, value: {'name': 'Alice'}"
```

## 🧙‍♂️ Advanced Usage

### 🧮 Custom Transformations

```python
# Apply transformations to extracted data
data = {"items": [{"price": 10}, {"price": 20}, {"price": 30}]}
total = dd(data).items[...].price(lambda prices: sum(prices))  # Returns 60

# Format all names to uppercase
data = {"users": [{"name": "alice"}, {"name": "bob"}]}
upper_names = dd(data).users[...].name(lambda names: [n.upper() for n in names])
# Returns ["ALICE", "BOB"]
```

### 🌐 Working with APIs

```python
import requests
from dd import dd

# Safely navigate through API response with a single ._ for the entire chain
response = requests.get("https://api.example.com/data").json()
first_tag = dd(response)._.data.items[0].tags[0]()  # Safely get the first tag, even if any part is None

# Process all items safely
all_prices = dd(response)._.data.items[...].price()  # Get all prices, handling nulls
```

## 📄 License

MIT
