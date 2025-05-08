from functools import partial
import unittest
from dd import dd, DDException


class TestDataDot(unittest.TestCase):
    def test_basic_access(self):
        data = {"users": [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]}
        self.assertEqual(dd(data).users[0].name(), "Alice")
        self.assertEqual(dd(data).users[1].age(), 25)

    def test_conversion(self):
        data = {"users": [{"name": "Alice", "age": 30}]}
        self.assertTrue(dd(data).users[0].age(lambda x: x >= 18))
        self.assertEqual(dd(data).users[0].name(lambda x: x.upper()), "ALICE")

    def test_null_safety(self):
        data = {"users": None}
        self.assertIsNone(dd(data)._.users[0].name())

        data = {"users": [{"name": "Alice"}, None]}
        self.assertEqual(dd(data)._.users[0].name(), "Alice")
        self.assertIsNone(dd(data)._.users[1].name())

    def test_null_safety_propagation(self):
        """测试 ._ 的传递性"""
        data = {"a": {"b": {"c": 1}}, "x": {"y": None}, "n": None}

        # 没有 ._ 会抛出异常
        with self.assertRaises(DDException):
            dd(data).n.anything()

        # 使用 ._ 后所有后续访问都安全
        self.assertIsNone(dd(data)._.n.anything.something.other())
        self.assertIsNone(dd(data)._.x.y.z.not_exist())
        self.assertEqual(dd(data)._.a.b.c(), 1)  # 有效路径仍然正常工作

    def test_expansion(self):
        data = {"users": [{"name": "Alice"}, {"name": "Bob"}, {"name": "Charlie"}]}
        self.assertEqual(dd(data).users[...].name(), ["Alice", "Bob", "Charlie"])

        config = {"server": {"ports": {"http": 80, "https": 443}}}
        self.assertEqual(dd(config).server.ports[...](), [80, 443])

    def test_error_handling(self):
        data = {"users": [{"name": "Alice"}]}
        with self.assertRaises(DDException) as context:
            dd(data).users[0].email()

        self.assertIn("Failed to get attribute 'email'", str(context.exception))
        self.assertIn("dd.users.[0].email", str(context.exception))

    def test_complex_operations(self):
        data = {"groups": [{"users": None}, {"users": [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 15}]}]}

        # Get all ages, handling nulls
        self.assertEqual(
            dd(data).groups[...]._.users[...].age(), [[], [30, 15]]
        )  # ._ 传递性使得后面的操作都是null-safe的

        # Get only adult names
        adults = (
            dd(data)
            .groups[...]
            ._.users[...](
                lambda users_groups: [
                    [user["name"] for user in (users or []) if user.get("age", 0) >= 18] for users in users_groups
                ]
            )
        )
        self.assertEqual(adults, [[], ["Alice"]])

    def test_custom_transformations(self):
        data = {"items": [{"price": 10}, {"price": 20}, {"price": 30}]}
        total = dd(data).items[...].price(lambda prices: sum(prices))
        self.assertEqual(total, 60)

    def test_expanded_array_shape_preservation(self):
        """测试在多维数组上使用[...]时保持数组的形状"""
        data = {"matrix": [[1, 2, 3], [4, 5, 6], [7, 8, 9]]}
        # 获取每一行的数据
        rows = dd(data).matrix[...]()
        self.assertEqual(rows, [[1, 2, 3], [4, 5, 6], [7, 8, 9]])

        # 获取每一行的第一个元素
        first_columns = dd(data).matrix[...][0]()
        self.assertEqual(first_columns, [1, 4, 7])

        # 操作每一行，对每行求和
        row_sums = dd(data).matrix[...](lambda rows: [sum(row) for row in rows])
        self.assertEqual(row_sums, [6, 15, 24])

    def test_nested_expansion(self):
        """测试嵌套的[...]操作"""
        data = {
            "departments": [
                {
                    "name": "Engineering",
                    "teams": [
                        {"name": "Frontend", "members": [{"name": "Alice"}, {"name": "Bob"}]},
                        {"name": "Backend", "members": [{"name": "Charlie"}, {"name": "Dave"}]},
                    ],
                },
                {
                    "name": "Marketing",
                    "teams": [
                        {"name": "Digital", "members": [{"name": "Eve"}, {"name": "Frank"}]},
                        {"name": "Brand", "members": [{"name": "Grace"}]},
                    ],
                },
            ]
        }

        # 获取所有部门中所有团队中所有成员的名字
        all_member_names = dd(data).departments[...].teams[...].members[...].name()
        self.assertEqual(all_member_names, [[["Alice", "Bob"], ["Charlie", "Dave"]], [["Eve", "Frank"], ["Grace"]]])

        # 使用转换函数扁平化结果
        flat_names = (
            dd(data)
            .departments[...]
            .teams[...]
            .members[...]
            .name(lambda names: [name for dept in names for team in dept for name in team])
        )
        self.assertEqual(flat_names, ["Alice", "Bob", "Charlie", "Dave", "Eve", "Frank", "Grace"])

    def test_dict_expansion_shape(self):
        """测试字典展开并保持键值对关系"""
        data = {
            "settings": {
                "display": {"theme": "dark", "font": "Arial"},
                "privacy": {"cookies": "accept", "tracking": "deny"},
            }
        }

        # 自定义函数保持键值对
        settings_with_keys = dd(data).settings[...](
            lambda values: [{k: v} for k, v in zip(dd(data).settings().keys(), values)]
        )
        self.assertEqual(
            settings_with_keys,
            [{"display": {"theme": "dark", "font": "Arial"}}, {"privacy": {"cookies": "accept", "tracking": "deny"}}],
        )

        # 获取所有嵌套设置的键值对
        all_settings = dd(data).settings[...][...](
            lambda values: [{k: v} for section in values for k, v in section.items()]
        )
        self.assertEqual(
            all_settings, [{"theme": "dark"}, {"font": "Arial"}, {"cookies": "accept"}, {"tracking": "deny"}]
        )

    def test_mixed_data_types(self):
        """测试混合数据类型的处理"""
        data = {
            "mixed": [
                {"type": "user", "value": {"name": "Alice", "age": 30}},
                {"type": "config", "value": ["debug", "verbose"]},
                {"type": "stats", "value": {"views": 100, "likes": 50}},
            ]
        }

        # 获取每种类型的值
        values = dd(data).mixed[...].value()
        self.assertEqual(values, [{"name": "Alice", "age": 30}, ["debug", "verbose"], {"views": 100, "likes": 50}])

        # 基于类型分组处理
        processed = dd(data).mixed[...](lambda items: {item["type"]: item["value"] for item in items})
        self.assertEqual(
            processed,
            {
                "user": {"name": "Alice", "age": 30},
                "config": ["debug", "verbose"],
                "stats": {"views": 100, "likes": 50},
            },
        )

    def test_custom_shape_transformations(self):
        """测试自定义形状转换"""
        data = {
            "products": [
                {
                    "id": "p1",
                    "name": "Phone",
                    "variants": [{"color": "red", "price": 100}, {"color": "blue", "price": 110}],
                },
                {
                    "id": "p2",
                    "name": "Laptop",
                    "variants": [{"color": "silver", "price": 800}, {"color": "black", "price": 820}],
                },
            ]
        }

        # 提取产品信息与变体信息，保持结构化关系
        product_info = dd(data).products[...](
            lambda products: [
                {
                    "product": {"id": p["id"], "name": p["name"]},
                    "variants": dd(p).variants[...](
                        lambda vars: [{"color": v["color"], "price": v["price"]} for v in vars]
                    ),
                }
                for p in products
            ]
        )

        expected = [
            {
                "product": {"id": "p1", "name": "Phone"},
                "variants": [{"color": "red", "price": 100}, {"color": "blue", "price": 110}],
            },
            {
                "product": {"id": "p2", "name": "Laptop"},
                "variants": [{"color": "silver", "price": 800}, {"color": "black", "price": 820}],
            },
        ]

        self.assertEqual(product_info, expected)

    def test_map_operations_on_expanded_elements(self):
        """测试对展开元素的映射操作"""
        # 场景1：简单用户列表
        data = {
            "users": [
                {"name": "Alice", "profile": {"age": 30, "city": "New York"}},
                {"name": "Bob", "profile": {"age": 25, "city": "Chicago"}},
                {"name": "Charlie", "profile": {"age": 35, "city": "San Francisco"}},
            ]
        }

        # 使用[...]展开users列表，然后直接访问每个用户的name
        names = dd(data).users[...].name()
        self.assertEqual(names, ["Alice", "Bob", "Charlie"])

        # 使用[...]展开users列表，然后访问每个用户的profile.city
        cities = dd(data).users[...].profile.city()
        self.assertEqual(cities, ["New York", "Chicago", "San Francisco"])

        # 场景2：嵌套数据结构
        data = {
            "departments": [
                {"name": "Engineering", "employees": [{"id": 1, "role": "Developer"}, {"id": 2, "role": "Designer"}]},
                {"name": "Marketing", "employees": [{"id": 3, "role": "Manager"}, {"id": 4, "role": "Copywriter"}]},
            ]
        }

        # 展开departments，然后获取每个部门的名称
        dept_names = dd(data).departments[...].name()
        self.assertEqual(dept_names, ["Engineering", "Marketing"])

        # 展开departments，然后展开每个部门的employees，获取每个员工的role
        roles = dd(data).departments[...].employees[...].role()
        self.assertEqual(roles, [["Developer", "Designer"], ["Manager", "Copywriter"]])

        # 场景3：混合类型和null值
        data = {
            "items": [
                {"type": "user", "data": {"username": "alice"}},
                {"type": "post"},
                {"type": "comment", "data": {"text": "Great post!"}},
            ]
        }

        # 使用null_safe处理可能为空的data字段
        item_types = dd(data).items[...].type()
        self.assertEqual(item_types, ["user", "post", "comment"])

        # 安全地访问data字段
        data_values = dd(data).items[...]._.data()
        self.assertEqual(data_values, [{"username": "alice"}, None, {"text": "Great post!"}])

        # 安全地尝试获取每个数据的第一个可用属性
        username_or_text = (
            dd(data)
            .items[...]
            ._.data(
                partial(map, (lambda d: d.get("username") if d and "username" in d else (d.get("text") if d else None)))
            )
        )
        self.assertEqual(list(username_or_text), ["alice", None, "Great post!"])

    def test_nested_circular_references(self):
        """测试嵌套的循环引用数据结构"""
        # 创建一个包含循环引用的数据结构
        data = {"name": "root"}
        # 使用引用而不是直接赋值，避免类型错误
        data["self"] = data
        data["children"] = [
            {"name": "child1", "parent": {"name": "root"}},
            {"name": "child2", "parent": {"name": "root"}},
        ]

        # 访问不应导致无限递归
        self.assertEqual(dd(data).name(), "root")
        self.assertEqual(dd(data).self.name(), "root")
        self.assertEqual(dd(data).children[0].name(), "child1")
        self.assertEqual(dd(data).children[0].parent.name(), "root")
        self.assertEqual(dd(data).children[1].parent.name(), "root")

        # 测试展开操作在循环引用情况下的表现
        children_names = dd(data).children[...].name()
        self.assertEqual(children_names, ["child1", "child2"])

    def test_large_nested_data(self):
        """测试处理大型嵌套数据结构的能力"""
        # 创建一个深度嵌套的大型数据结构
        data = {"level": 0}
        current = data

        # 创建深度为20的嵌套结构
        for i in range(1, 21):
            current["next"] = {"level": i}
            current = current["next"]

        # 测试能否正确访问深层数据
        self.assertEqual(dd(data).next.next.next.next.next.level(), 5)

        # 测试一个很长的访问链
        self.assertEqual(
            dd(
                data
            ).next.next.next.next.next.next.next.next.next.next.next.next.next.next.next.next.next.next.next.next.level(),
            20,
        )

        # 测试长访问链中间某一点的null safety
        current = data
        for i in range(10):
            current = current["next"]
        current["next"] = None

        # 检查正常访问是否会抛出异常
        with self.assertRaises(DDException):
            dd(data).next.next.next.next.next.next.next.next.next.next.next.level()

        # 使用 ._ 后应该返回 None
        self.assertIsNone(dd(data)._.next.next.next.next.next.next.next.next.next.next.next.level())

    def test_heterogeneous_data_expansion(self):
        """测试处理不同类型数据的展开能力"""
        data = {
            "mixed_list": [
                123,
                "string",
                {"key": "value"},
                ["nested", "list"],
                None,
                True,
                {"items": [1, 2, {"deep": "nested"}]},
            ],
            "dict_with_different_types": {
                "number": 42,
                "string": "text",
                "boolean": True,
                "none": None,
                "list": [1, 2, 3],
                "dict": {"a": 1},
            },
        }

        # 展开混合列表
        expanded = dd(data).mixed_list[...]()
        self.assertEqual(len(expanded), 7)
        self.assertEqual(expanded[0], 123)
        self.assertEqual(expanded[2], {"key": "value"})

        # 对不规则数据进行深层展开和转换
        complex_result = dd(data).mixed_list[...](
            lambda items: [
                type(item).__name__ if not isinstance(item, dict) else [k for k in item.keys()] for item in items
            ]
        )
        self.assertEqual(complex_result, ["int", "str", ["key"], "list", "NoneType", "bool", ["items"]])

        # 展开字典
        dict_values = dd(data).dict_with_different_types[...]()
        self.assertEqual(len(dict_values), 6)

        # 确保展开的值与原始值匹配
        dict_keys = list(data["dict_with_different_types"].keys())
        for i, key in enumerate(dict_keys):
            self.assertEqual(dd(data).dict_with_different_types[key](), data["dict_with_different_types"][key])

    def test_error_recovery_and_path_reporting(self):
        """测试错误恢复和路径报告功能"""
        data = {
            "users": [
                {"id": 1, "name": "Alice", "metadata": {"tags": ["admin", "active"]}},
                {"id": 2, "name": "Bob", "metadata": None},
            ]
        }

        # 测试详细的错误路径报告
        with self.assertRaises(DDException) as context:
            dd(data).users[2].name()  # 访问不存在的索引

        error_message = str(context.exception)
        self.assertIn("Failed to get attribute", error_message)
        self.assertIn("dd.users.[2]", error_message)

        # 测试嵌套属性的错误路径
        with self.assertRaises(DDException) as context:
            dd(data).users[1].metadata.tags[0]()

        error_message = str(context.exception)
        self.assertIn("dd.users.[1].metadata.tags", error_message)

        # 测试空值安全后的路径继续报告
        # 即使有._ 也应该在错误信息中保留完整路径
        with self.assertRaises(DDException) as context:
            dd(data)._.non_existent.another.something(lambda _: 1 / 0)

        error_message = str(context.exception)
        self.assertIn("dd.non_existent", error_message)

    def test_function_composition(self):
        """测试函数组合和链式处理"""
        data = {
            "products": [
                {"id": "p1", "price": 100, "stock": 5},
                {"id": "p2", "price": 200, "stock": 0},
                {"id": "p3", "price": 150, "stock": 10},
            ]
        }

        # 测试组合多个转换函数
        def filter_in_stock(products):
            return dd([p for p in products if p["stock"] > 0])

        def calculate_value(products):
            return sum(p["price"] * p["stock"] for p in products)

        # 链式应用转换
        in_stock_products = dd(data).products[...](filter_in_stock)()
        self.assertEqual(len(in_stock_products), 2)
        self.assertEqual(in_stock_products[0]["id"], "p1")
        self.assertEqual(in_stock_products[1]["id"], "p3")

        # 计算库存总价值
        total_value = dd(data).products[...](filter_in_stock)(calculate_value)
        self.assertEqual(total_value, 100 * 5 + 150 * 10)

        # 测试对转换后结果的进一步处理
        formatted_result = dd(data).products[...](filter_in_stock)(
            lambda products: {p["id"]: f"${p['price'] * p['stock']}" for p in products}
        )
        self.assertEqual(formatted_result, {"p1": "$500", "p3": "$1500"})

    def test_conditional_data_access(self):
        """测试条件数据访问"""
        data = {
            "settings": {
                "features": {
                    "feature1": {"enabled": True, "config": {"timeout": 30}},
                    "feature2": {"enabled": False, "config": {"timeout": 60}},
                    "feature3": {"enabled": True, "config": None},
                }
            }
        }

        # 测试条件访问：获取所有已启用的功能的配置
        def get_enabled_configs(features):
            return {name: feature["config"] for name, feature in features.items() if feature["enabled"]}

        enabled_configs = dd(data).settings.features(get_enabled_configs)
        self.assertEqual(enabled_configs, {"feature1": {"timeout": 30}, "feature3": None})

        # 测试条件展开：只展开启用的功能
        def expand_enabled_features(features):
            return [
                {"name": name, "config": feature["config"]} for name, feature in features.items() if feature["enabled"]
            ]

        enabled_features = dd(data).settings.features(expand_enabled_features)
        self.assertEqual(
            enabled_features, [{"name": "feature1", "config": {"timeout": 30}}, {"name": "feature3", "config": None}]
        )

        # 测试空值安全与条件访问组合
        timeout_values = (
            dd(data).settings.features[...]._.config._.timeout(lambda timeouts: [t for t in timeouts if t is not None])
        )
        self.assertEqual(timeout_values, [30, 60])

    def test_dynamic_key_access(self):
        """测试动态键访问和路径构建"""
        data = {
            "database": {
                "tables": {
                    "users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
                    "posts": [{"id": 101, "title": "Hello"}, {"id": 102, "title": "World"}],
                }
            }
        }

        # 动态构建访问路径
        tables = ["users", "posts"]

        all_items = []
        for table in tables:
            items = dd(data).database.tables[table][...]()
            all_items.extend(items)

        self.assertEqual(len(all_items), 4)

        # 测试构建更复杂的动态访问路径
        def access_by_path(data, path_parts):
            result = dd(data)
            for part in path_parts:
                if isinstance(part, int):
                    result = result[part]
                elif part == "...":
                    result = result[...]
                else:
                    result = getattr(result, part)
            return result()

        # 动态构建不同的访问路径
        user_names = access_by_path(data, ["database", "tables", "users", "...", "name"])
        self.assertEqual(user_names, ["Alice", "Bob"])

        post_titles = access_by_path(data, ["database", "tables", "posts", "...", "title"])
        self.assertEqual(post_titles, ["Hello", "World"])

    def test_performance_with_complex_operations(self):
        """测试在复杂操作下的性能表现"""
        import time

        # 创建一个大型数据结构
        data = {
            "records": [
                {
                    "id": i,
                    "values": [j for j in range(100)],
                    "metadata": {
                        "tags": [f"tag{k}" for k in range(20)],
                        "created": "2023-01-01",
                        "updated": "2023-01-02",
                    },
                }
                for i in range(100)
            ]
        }

        # 测试多重展开和过滤操作的性能
        start_time = time.time()

        # 复杂操作：获取所有偶数ID记录的第一个标签
        result = dd(data).records[...](lambda records: [r["metadata"]["tags"][0] for r in records if r["id"] % 2 == 0])

        end_time = time.time()
        elapsed = end_time - start_time

        # 验证结果正确性
        self.assertEqual(len(result), 50)  # 50个偶数ID
        self.assertEqual(result[0], "tag0")

        # 性能检查仅作为参考，不严格断言时间
        print(f"Complex operation completed in {elapsed:.6f} seconds")

        # 更复杂的操作：获取每个记录的平均值和标签数量
        start_time = time.time()

        result = dd(data).records[...](
            lambda records: [
                {
                    "id": r["id"],
                    "avg_value": sum(r["values"]) / len(r["values"]),
                    "tag_count": len(r["metadata"]["tags"]),
                }
                for r in records
            ]
        )

        end_time = time.time()
        elapsed = end_time - start_time

        # 验证结果
        self.assertEqual(len(result), 100)
        self.assertEqual(result[0]["avg_value"], 49.5)  # 0-99的平均值
        self.assertEqual(result[0]["tag_count"], 20)

        print(f"More complex operation completed in {elapsed:.6f} seconds")

    def test_edge_cases(self):
        """测试各种边缘情况"""
        # 空数据
        self.assertEqual(dd({})._(lambda x: "empty"), "empty")
        self.assertIsNone(dd(None)._())

        # 极端值
        data = {"min": float("-inf"), "max": float("inf"), "nan": float("nan")}
        self.assertEqual(dd(data).min(), float("-inf"))
        self.assertEqual(dd(data).max(), float("inf"))
        self.assertTrue(isinstance(dd(data).nan(), float))

        # 特殊字符键
        data = {
            "!@#$%^&*()": "special chars",
            "   ": "spaces",
            "": "empty string",
            123: "numeric key",
            True: "boolean key",
            (1, 2): "tuple key",
        }

        self.assertEqual(dd(data)["!@#$%^&*()"](), "special chars")
        self.assertEqual(dd(data)["   "](), "spaces")
        self.assertEqual(dd(data)[""](), "empty string")
        self.assertEqual(dd(data)[123](), "numeric key")
        self.assertEqual(dd(data)[True](), "boolean key")
        self.assertEqual(dd(data)[(1, 2)](), "tuple key")

        # Unicode和国际化字符
        data = {"中文": "Chinese", "русский": "Russian", "日本語": "Japanese", "العربية": "Arabic", "😀": "Emoji"}

        self.assertEqual(dd(data)["中文"](), "Chinese")
        self.assertEqual(dd(data)["русский"](), "Russian")
        self.assertEqual(dd(data)["日本語"](), "Japanese")
        self.assertEqual(dd(data)["العربية"](), "Arabic")
        self.assertEqual(dd(data)["😀"](), "Emoji")

    def test_highly_nested_expansions(self):
        """测试高度嵌套的展开操作"""
        # 创建一个深度嵌套的数据结构
        data = {
            "level1": [
                {
                    "name": "A",
                    "level2": [
                        {"name": "A1", "level3": [{"name": "A1a", "value": 1}, {"name": "A1b", "value": 2}]},
                        {"name": "A2", "level3": [{"name": "A2a", "value": 3}, {"name": "A2b", "value": 4}]},
                    ],
                },
                {
                    "name": "B",
                    "level2": [
                        {"name": "B1", "level3": [{"name": "B1a", "value": 5}, {"name": "B1b", "value": 6}]},
                        {"name": "B2", "level3": None},  # 故意放置一个None
                    ],
                },
            ]
        }

        # 测试高度嵌套展开 - 获取所有最深层的名称
        deepest_names = dd(data).level1[...].level2[...]._.level3[...]._.name()
        expected = [[["A1a", "A1b"], ["A2a", "A2b"]], [["B1a", "B1b"], []]]
        self.assertEqual(deepest_names, expected)

        # 获取所有值并计算总和
        all_values = dd(data).level1[...].level2[...]._.level3[...]._.value()
        # 扁平化并过滤None
        flat_values = [v for sublist1 in all_values for sublist2 in sublist1 for v in (sublist2 or [])]
        self.assertEqual(sum(flat_values), 21)  # 1+2+3+4+5+6=21

        # 测试在多级展开中应用转换
        transformed = dd(data).level1[...].level2[...]._.level3[...].name()

        expected = [[["A1a", "A1b"], ["A2a", "A2b"]], [["B1a", "B1b"], []]]
        self.assertEqual(transformed, expected)

        # 测试展开后扁平化结果
        def flatten_nested_list(nested_list):
            result = []

            def _flatten(items):
                for item in items:
                    if isinstance(item, list):
                        _flatten(item)
                    else:
                        result.append(item)

            _flatten(nested_list)
            return result

        flattened_names = (
            dd(data).level1[...].level2[...]._.level3[...]._.name(lambda names: flatten_nested_list(names))
        )

        self.assertEqual(flattened_names, ["A1a", "A1b", "A2a", "A2b", "B1a", "B1b"])


if __name__ == "__main__":
    unittest.main()
