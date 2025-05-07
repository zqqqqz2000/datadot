import unittest
from src.dd import dd, DDException


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
        self.assertIn("dd.users[0].email", str(context.exception))

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
                    )(),
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


if __name__ == "__main__":
    unittest.main()

