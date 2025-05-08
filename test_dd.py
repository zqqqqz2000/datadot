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
        """Test the transitivity of ._"""
        data = {"a": {"b": {"c": 1}}, "x": {"y": None}, "n": None}

        # Without ._ will raise an exception
        with self.assertRaises(DDException):
            dd(data).n.anything()

        # Using ._ makes all subsequent accesses safe
        self.assertIsNone(dd(data)._.n.anything.something.other())
        self.assertIsNone(dd(data)._.x.y.z.not_exist())
        self.assertEqual(dd(data)._.a.b.c(), 1)  # Valid paths still work normally

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
        )  # The transitivity of ._ makes subsequent operations null-safe

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
        """Test preserving array shape when using [...] on multidimensional arrays"""
        data = {"matrix": [[1, 2, 3], [4, 5, 6], [7, 8, 9]]}
        # Get each row's data
        rows = dd(data).matrix[...]()
        self.assertEqual(rows, [[1, 2, 3], [4, 5, 6], [7, 8, 9]])

        # Get the first element of each row
        first_columns = dd(data).matrix[...][0]()
        self.assertEqual(first_columns, [1, 4, 7])

        # Operate on each row, sum each row
        row_sums = dd(data).matrix[...](lambda rows: [sum(row) for row in rows])
        self.assertEqual(row_sums, [6, 15, 24])

    def test_nested_expansion(self):
        """Test nested [...] operations"""
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

        # Get the names of all members in all teams in all departments
        all_member_names = dd(data).departments[...].teams[...].members[...].name()
        self.assertEqual(all_member_names, [[["Alice", "Bob"], ["Charlie", "Dave"]], [["Eve", "Frank"], ["Grace"]]])

        # Use transform function to flatten the result
        flat_names = (
            dd(data)
            .departments[...]
            .teams[...]
            .members[...]
            .name(lambda names: [name for dept in names for team in dept for name in team])
        )
        self.assertEqual(flat_names, ["Alice", "Bob", "Charlie", "Dave", "Eve", "Frank", "Grace"])

    def test_dict_expansion_shape(self):
        """Test dictionary expansion while maintaining key-value relationships"""
        data = {
            "settings": {
                "display": {"theme": "dark", "font": "Arial"},
                "privacy": {"cookies": "accept", "tracking": "deny"},
            }
        }

        # Custom function to maintain key-value pairs
        settings_with_keys = dd(data).settings[...](
            lambda values: [{k: v} for k, v in zip(dd(data).settings().keys(), values)]
        )
        self.assertEqual(
            settings_with_keys,
            [{"display": {"theme": "dark", "font": "Arial"}}, {"privacy": {"cookies": "accept", "tracking": "deny"}}],
        )

        # Get all nested settings key-value pairs
        all_settings = dd(data).settings[...][...](
            lambda values: [{k: v} for section in values for k, v in section.items()]
        )
        self.assertEqual(
            all_settings, [{"theme": "dark"}, {"font": "Arial"}, {"cookies": "accept"}, {"tracking": "deny"}]
        )

    def test_mixed_data_types(self):
        """Test processing of mixed data types"""
        data = {
            "mixed": [
                {"type": "user", "value": {"name": "Alice", "age": 30}},
                {"type": "config", "value": ["debug", "verbose"]},
                {"type": "stats", "value": {"views": 100, "likes": 50}},
            ]
        }

        # Get the value of each type
        values = dd(data).mixed[...].value()
        self.assertEqual(values, [{"name": "Alice", "age": 30}, ["debug", "verbose"], {"views": 100, "likes": 50}])

        # Process by type grouping
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
        """Test custom shape transformations"""
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

        # Extract product info and variant info, maintaining structured relationships
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
        """Test mapping operations on expanded elements"""
        # Scenario 1: Simple user list
        data = {
            "users": [
                {"name": "Alice", "profile": {"age": 30, "city": "New York"}},
                {"name": "Bob", "profile": {"age": 25, "city": "Chicago"}},
                {"name": "Charlie", "profile": {"age": 35, "city": "San Francisco"}},
            ]
        }

        # Use [...] to expand the users list, then directly access each user's name
        names = dd(data).users[...].name()
        self.assertEqual(names, ["Alice", "Bob", "Charlie"])

        # Use [...] to expand the users list, then access each user's profile.city
        cities = dd(data).users[...].profile.city()
        self.assertEqual(cities, ["New York", "Chicago", "San Francisco"])

        # Scenario 2: Nested data structure
        data = {
            "departments": [
                {"name": "Engineering", "employees": [{"id": 1, "role": "Developer"}, {"id": 2, "role": "Designer"}]},
                {"name": "Marketing", "employees": [{"id": 3, "role": "Manager"}, {"id": 4, "role": "Copywriter"}]},
            ]
        }

        # Expand departments, then get each department's name
        dept_names = dd(data).departments[...].name()
        self.assertEqual(dept_names, ["Engineering", "Marketing"])

        # Expand departments, then expand each department's employees, and get each employee's role
        roles = dd(data).departments[...].employees[...].role()
        self.assertEqual(roles, [["Developer", "Designer"], ["Manager", "Copywriter"]])

        # Scenario 3: Mixed types and null values
        data = {
            "items": [
                {"type": "user", "data": {"username": "alice"}},
                {"type": "post"},
                {"type": "comment", "data": {"text": "Great post!"}},
            ]
        }

        # Use null_safe to handle potentially empty data fields
        item_types = dd(data).items[...].type()
        self.assertEqual(item_types, ["user", "post", "comment"])

        # Safely access the data field
        data_values = dd(data).items[...]._.data()
        self.assertEqual(data_values, [{"username": "alice"}, None, {"text": "Great post!"}])

        # Safely try to get the first available attribute for each data
        username_or_text = (
            dd(data)
            .items[...]
            ._.data(
                partial(map, (lambda d: d.get("username") if d and "username" in d else (d.get("text") if d else None)))
            )
        )
        self.assertEqual(list(username_or_text), ["alice", None, "Great post!"])

    def test_nested_circular_references(self):
        """Test nested circular reference data structures"""
        # Create a data structure with circular references
        data = {"name": "root"}
        # Use references instead of direct assignment to avoid type errors
        data["self"] = data
        data["children"] = [
            {"name": "child1", "parent": {"name": "root"}},
            {"name": "child2", "parent": {"name": "root"}},
        ]

        # Access should not lead to infinite recursion
        self.assertEqual(dd(data).name(), "root")
        self.assertEqual(dd(data).self.name(), "root")
        self.assertEqual(dd(data).children[0].name(), "child1")
        self.assertEqual(dd(data).children[0].parent.name(), "root")
        self.assertEqual(dd(data).children[1].parent.name(), "root")

        # Test expansion operations with circular references
        children_names = dd(data).children[...].name()
        self.assertEqual(children_names, ["child1", "child2"])

    def test_large_nested_data(self):
        """Test the ability to handle large nested data structures"""
        # Create a deeply nested large data structure
        data = {"level": 0}
        current = data

        # Create a nested structure with depth of 20
        for i in range(1, 21):
            current["next"] = {"level": i}
            current = current["next"]

        # Test the ability to correctly access deep data
        self.assertEqual(dd(data).next.next.next.next.next.level(), 5)

        # Test a very long access chain
        self.assertEqual(
            dd(
                data
            ).next.next.next.next.next.next.next.next.next.next.next.next.next.next.next.next.next.next.next.next.level(),
            20,
        )

        # Test null safety at some point in a long access chain
        current = data
        for i in range(10):
            current = current["next"]
        current["next"] = None

        # Check if normal access would throw an exception
        with self.assertRaises(DDException):
            dd(data).next.next.next.next.next.next.next.next.next.next.next.level()

        # Using ._ should return None
        self.assertIsNone(dd(data)._.next.next.next.next.next.next.next.next.next.next.next.level())

    def test_heterogeneous_data_expansion(self):
        """Test the ability to expand different types of data"""
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

        # Expand mixed list
        expanded = dd(data).mixed_list[...]()
        self.assertEqual(len(expanded), 7)
        self.assertEqual(expanded[0], 123)
        self.assertEqual(expanded[2], {"key": "value"})

        # Perform deep expansion and transformation on irregular data
        complex_result = dd(data).mixed_list[...](
            lambda items: [
                type(item).__name__ if not isinstance(item, dict) else [k for k in item.keys()] for item in items
            ]
        )
        self.assertEqual(complex_result, ["int", "str", ["key"], "list", "NoneType", "bool", ["items"]])

        # Expand dictionary
        dict_values = dd(data).dict_with_different_types[...]()
        self.assertEqual(len(dict_values), 6)

        # Ensure expanded values match original values
        dict_keys = list(data["dict_with_different_types"].keys())
        for i, key in enumerate(dict_keys):
            self.assertEqual(dd(data).dict_with_different_types[key](), data["dict_with_different_types"][key])

    def test_error_recovery_and_path_reporting(self):
        """Test error recovery and path reporting functionality"""
        data = {
            "users": [
                {"id": 1, "name": "Alice", "metadata": {"tags": ["admin", "active"]}},
                {"id": 2, "name": "Bob", "metadata": None},
            ]
        }

        # Test detailed error path reporting
        with self.assertRaises(DDException) as context:
            dd(data).users[2].name()  # Access non-existent index

        error_message = str(context.exception)
        self.assertIn("Failed to get attribute", error_message)
        self.assertIn("dd.users.[2]", error_message)

        # Test error path for nested attributes
        with self.assertRaises(DDException) as context:
            dd(data).users[1].metadata.tags[0]()

        error_message = str(context.exception)
        self.assertIn("dd.users.[1].metadata.tags", error_message)

        # Test continued path reporting after null safety
        # Even with ._ should preserve complete path in error message
        with self.assertRaises(DDException) as context:
            dd(data)._.non_existent.another.something(lambda _: 1 / 0)

        error_message = str(context.exception)
        self.assertIn("dd.non_existent", error_message)

    def test_function_composition(self):
        """Test function composition and chained processing"""
        data = {
            "products": [
                {"id": "p1", "price": 100, "stock": 5},
                {"id": "p2", "price": 200, "stock": 0},
                {"id": "p3", "price": 150, "stock": 10},
            ]
        }

        # Test combining multiple transformation functions
        def filter_in_stock(products):
            return dd([p for p in products if p["stock"] > 0])

        def calculate_value(products):
            return sum(p["price"] * p["stock"] for p in products)

        # Chain-apply transformations
        in_stock_products = dd(data).products[...](filter_in_stock)()
        self.assertEqual(len(in_stock_products), 2)
        self.assertEqual(in_stock_products[0]["id"], "p1")
        self.assertEqual(in_stock_products[1]["id"], "p3")

        # Calculate total inventory value
        total_value = dd(data).products[...](filter_in_stock)(calculate_value)
        self.assertEqual(total_value, 100 * 5 + 150 * 10)

        # Test further processing of transformed results
        formatted_result = dd(data).products[...](filter_in_stock)(
            lambda products: {p["id"]: f"${p['price'] * p['stock']}" for p in products}
        )
        self.assertEqual(formatted_result, {"p1": "$500", "p3": "$1500"})

    def test_conditional_data_access(self):
        """Test conditional data access"""
        data = {
            "settings": {
                "features": {
                    "feature1": {"enabled": True, "config": {"timeout": 30}},
                    "feature2": {"enabled": False, "config": {"timeout": 60}},
                    "feature3": {"enabled": True, "config": None},
                }
            }
        }

        # Test conditional access: get configs of all enabled features
        def get_enabled_configs(features):
            return {name: feature["config"] for name, feature in features.items() if feature["enabled"]}

        enabled_configs = dd(data).settings.features(get_enabled_configs)
        self.assertEqual(enabled_configs, {"feature1": {"timeout": 30}, "feature3": None})

        # Test conditional expansion: only expand enabled features
        def expand_enabled_features(features):
            return [
                {"name": name, "config": feature["config"]} for name, feature in features.items() if feature["enabled"]
            ]

        enabled_features = dd(data).settings.features(expand_enabled_features)
        self.assertEqual(
            enabled_features, [{"name": "feature1", "config": {"timeout": 30}}, {"name": "feature3", "config": None}]
        )

        # Test combining null safety with conditional access
        timeout_values = (
            dd(data).settings.features[...]._.config._.timeout(lambda timeouts: [t for t in timeouts if t is not None])
        )
        self.assertEqual(timeout_values, [30, 60])

    def test_dynamic_key_access(self):
        """Test dynamic key access and path building"""
        data = {
            "database": {
                "tables": {
                    "users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
                    "posts": [{"id": 101, "title": "Hello"}, {"id": 102, "title": "World"}],
                }
            }
        }

        # Dynamically build access paths
        tables = ["users", "posts"]

        all_items = []
        for table in tables:
            items = dd(data).database.tables[table][...]()
            all_items.extend(items)

        self.assertEqual(len(all_items), 4)

        # Test building more complex dynamic access paths
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

        # Dynamically build different access paths
        user_names = access_by_path(data, ["database", "tables", "users", "...", "name"])
        self.assertEqual(user_names, ["Alice", "Bob"])

        post_titles = access_by_path(data, ["database", "tables", "posts", "...", "title"])
        self.assertEqual(post_titles, ["Hello", "World"])

    def test_performance_with_complex_operations(self):
        """Test performance with complex operations"""
        import time

        # Create a large data structure
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

        # Test performance of multiple expansions and filtering operations
        start_time = time.time()

        # Complex operation: get the first tag of all records with even IDs
        result = dd(data).records[...](lambda records: [r["metadata"]["tags"][0] for r in records if r["id"] % 2 == 0])

        end_time = time.time()
        elapsed = end_time - start_time

        # Verify result correctness
        self.assertEqual(len(result), 50)  # 50 even IDs
        self.assertEqual(result[0], "tag0")

        # Performance check only as reference, not strict time assertion
        print(f"Complex operation completed in {elapsed:.6f} seconds")

        # More complex operation: get average value and tag count for each record
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

        # Verify results
        self.assertEqual(len(result), 100)
        self.assertEqual(result[0]["avg_value"], 49.5)  # Average of 0-99
        self.assertEqual(result[0]["tag_count"], 20)

        print(f"More complex operation completed in {elapsed:.6f} seconds")

    def test_edge_cases(self):
        """Test various edge cases"""
        # Empty data
        self.assertEqual(dd({})._(lambda x: "empty"), "empty")
        self.assertIsNone(dd(None)._())

        # Extreme values
        data = {"min": float("-inf"), "max": float("inf"), "nan": float("nan")}
        self.assertEqual(dd(data).min(), float("-inf"))
        self.assertEqual(dd(data).max(), float("inf"))
        self.assertTrue(isinstance(dd(data).nan(), float))

        # Special character keys
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

        # Unicode and internationalization characters
        data = {"中文": "Chinese", "русский": "Russian", "日本語": "Japanese", "العربية": "Arabic", "😀": "Emoji"}

        self.assertEqual(dd(data)["中文"](), "Chinese")
        self.assertEqual(dd(data)["русский"](), "Russian")
        self.assertEqual(dd(data)["日本語"](), "Japanese")
        self.assertEqual(dd(data)["العربية"](), "Arabic")
        self.assertEqual(dd(data)["😀"](), "Emoji")

    def test_highly_nested_expansions(self):
        """Test highly nested expansion operations"""
        # Create a deeply nested data structure
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
                        {"name": "B2", "level3": None},  # Deliberately place a None
                    ],
                },
            ]
        }

        # Test highly nested expansion - get all names from the deepest layer
        deepest_names = dd(data).level1[...].level2[...]._.level3[...]._.name()
        expected = [[["A1a", "A1b"], ["A2a", "A2b"]], [["B1a", "B1b"], []]]
        self.assertEqual(deepest_names, expected)

        # Get all values and calculate sum
        all_values = dd(data).level1[...].level2[...]._.level3[...]._.value()
        # Flatten and filter None
        flat_values = [v for sublist1 in all_values for sublist2 in sublist1 for v in (sublist2 or [])]
        self.assertEqual(sum(flat_values), 21)  # 1+2+3+4+5+6=21

        # Test applying transformations in multi-level expansions
        transformed = dd(data).level1[...].level2[...]._.level3[...].name()

        expected = [[["A1a", "A1b"], ["A2a", "A2b"]], [["B1a", "B1b"], []]]
        self.assertEqual(transformed, expected)

        # Test flattening results after expansion
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
