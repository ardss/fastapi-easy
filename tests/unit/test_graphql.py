"""Unit tests for GraphQL support"""

import pytest
from fastapi_easy.graphql import (
    GraphQLField,
    GraphQLType,
    GraphQLQuery,
    GraphQLMutation,
    GraphQLSchema,
    GraphQLAdapter,
    GraphQLConfig,
    create_graphql_schema_from_model,
)


class TestGraphQLField:
    """Test GraphQLField"""
    
    def test_field_initialization(self):
        """Test field initialization"""
        field = GraphQLField("name", "String")
        
        assert field.name == "name"
        assert field.field_type == "String"
        assert field.required is False
        assert field.list_type is False
    
    def test_field_required(self):
        """Test required field"""
        field = GraphQLField("id", "Int", required=True)
        
        assert field.required is True
    
    def test_field_list_type(self):
        """Test list type field"""
        field = GraphQLField("items", "String", list_type=True)
        
        assert field.list_type is True
    
    def test_field_to_schema(self):
        """Test converting field to schema"""
        field = GraphQLField("name", "String", required=True)
        schema = field.to_schema()
        
        assert schema == "name: String!"
    
    def test_field_list_to_schema(self):
        """Test converting list field to schema"""
        field = GraphQLField("items", "String", list_type=True, required=True)
        schema = field.to_schema()
        
        assert schema == "items: [String]!"


class TestGraphQLType:
    """Test GraphQLType"""
    
    def test_type_initialization(self):
        """Test type initialization"""
        type_def = GraphQLType("User")
        
        assert type_def.name == "User"
        assert type_def.fields == []
    
    def test_add_field(self):
        """Test adding field to type"""
        type_def = GraphQLType("User")
        field = GraphQLField("name", "String")
        
        type_def.add_field(field)
        
        assert len(type_def.fields) == 1
        assert type_def.fields[0].name == "name"
    
    def test_type_to_schema(self):
        """Test converting type to schema"""
        type_def = GraphQLType("User")
        type_def.add_field(GraphQLField("id", "Int", required=True))
        type_def.add_field(GraphQLField("name", "String", required=True))
        
        schema = type_def.to_schema()
        
        assert "type User" in schema
        assert "id: Int!" in schema
        assert "name: String!" in schema


class TestGraphQLQuery:
    """Test GraphQLQuery"""
    
    def test_query_initialization(self):
        """Test query initialization"""
        query = GraphQLQuery("getUser", "User")
        
        assert query.name == "getUser"
        assert query.return_type == "User"
        assert query.required is False
    
    def test_add_arg(self):
        """Test adding argument to query"""
        query = GraphQLQuery("getUser", "User")
        query.add_arg("id", "Int!")
        
        assert "id" in query.args
        assert query.args["id"] == "Int!"
    
    def test_query_to_schema(self):
        """Test converting query to schema"""
        query = GraphQLQuery("getUser", "User")
        query.add_arg("id", "Int!")
        
        schema = query.to_schema()
        
        assert "getUser(id: Int!): User" in schema
    
    def test_query_required_return(self):
        """Test query with required return type"""
        query = GraphQLQuery("getUser", "User", required=True)
        schema = query.to_schema()
        
        assert "User!" in schema


class TestGraphQLMutation:
    """Test GraphQLMutation"""
    
    def test_mutation_initialization(self):
        """Test mutation initialization"""
        mutation = GraphQLMutation("createUser", "User")
        
        assert mutation.name == "createUser"
        assert mutation.return_type == "User"
    
    def test_add_arg(self):
        """Test adding argument to mutation"""
        mutation = GraphQLMutation("createUser", "User")
        mutation.add_arg("input", "UserInput!")
        
        assert "input" in mutation.args
    
    def test_mutation_to_schema(self):
        """Test converting mutation to schema"""
        mutation = GraphQLMutation("createUser", "User")
        mutation.add_arg("input", "UserInput!")
        
        schema = mutation.to_schema()
        
        assert "createUser(input: UserInput!): User" in schema


class TestGraphQLSchema:
    """Test GraphQLSchema"""
    
    def test_schema_initialization(self):
        """Test schema initialization"""
        schema = GraphQLSchema()
        
        assert schema.types == {}
        assert schema.queries == []
        assert schema.mutations == []
    
    def test_add_type(self):
        """Test adding type to schema"""
        schema = GraphQLSchema()
        type_def = GraphQLType("User")
        
        schema.add_type(type_def)
        
        assert "User" in schema.types
    
    def test_add_query(self):
        """Test adding query to schema"""
        schema = GraphQLSchema()
        query = GraphQLQuery("getUser", "User")
        
        schema.add_query(query)
        
        assert len(schema.queries) == 1
    
    def test_add_mutation(self):
        """Test adding mutation to schema"""
        schema = GraphQLSchema()
        mutation = GraphQLMutation("createUser", "User")
        
        schema.add_mutation(mutation)
        
        assert len(schema.mutations) == 1
    
    def test_schema_to_string(self):
        """Test converting schema to string"""
        schema = GraphQLSchema()
        
        type_def = GraphQLType("User")
        type_def.add_field(GraphQLField("id", "Int", required=True))
        schema.add_type(type_def)
        
        query = GraphQLQuery("getUser", "User")
        query.add_arg("id", "Int!")
        schema.add_query(query)
        
        schema_str = schema.to_schema_string()
        
        assert "type User" in schema_str
        assert "type Query" in schema_str
        assert "getUser" in schema_str


class TestGraphQLAdapter:
    """Test GraphQLAdapter"""
    
    def test_adapter_initialization(self):
        """Test adapter initialization"""
        class MockModel:
            pass
        
        type_def = GraphQLType("User")
        adapter = GraphQLAdapter(MockModel, type_def)
        
        assert adapter.model == MockModel
        assert adapter.schema == type_def
    
    def test_execute_query(self):
        """Test executing query"""
        class MockModel:
            pass
        
        type_def = GraphQLType("User")
        adapter = GraphQLAdapter(MockModel, type_def)
        
        result = adapter.execute_query("query { getUser(id: 1) { id name } }")
        
        assert isinstance(result, dict)
        assert "data" in result


class TestGraphQLConfig:
    """Test GraphQLConfig"""
    
    def test_default_config(self):
        """Test default configuration"""
        config = GraphQLConfig()
        
        assert config.enabled is True
        assert config.endpoint == "/graphql"
        assert config.playground is True
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = GraphQLConfig(
            enabled=False,
            endpoint="/api/graphql",
            playground=False,
        )
        
        assert config.enabled is False
        assert config.endpoint == "/api/graphql"
        assert config.playground is False


class TestCreateGraphQLSchema:
    """Test create_graphql_schema_from_model"""
    
    def test_create_schema_from_model(self):
        """Test creating schema from model"""
        # Mock SQLAlchemy model
        class MockColumn:
            def __init__(self, name, type_str, nullable=False):
                self.name = name
                self.type = type(str(type_str), (), {})()
                self.nullable = nullable
            
            def __str__(self):
                return self.name
        
        class MockTable:
            columns = [
                MockColumn("id", "INTEGER", nullable=False),
                MockColumn("name", "VARCHAR", nullable=False),
                MockColumn("email", "VARCHAR", nullable=True),
            ]
        
        class MockModel:
            __table__ = MockTable()
        
        schema = create_graphql_schema_from_model(MockModel, "User")
        
        assert "User" in schema.types
        assert len(schema.queries) > 0
        assert len(schema.mutations) > 0
    
    def test_schema_has_default_queries(self):
        """Test schema has default queries"""
        class MockColumn:
            def __init__(self, name, type_str, nullable=False):
                self.name = name
                self.type = type(str(type_str), (), {})()
                self.nullable = nullable
        
        class MockTable:
            columns = [MockColumn("id", "INTEGER", nullable=False)]
        
        class MockModel:
            __table__ = MockTable()
        
        schema = create_graphql_schema_from_model(MockModel, "User")
        
        query_names = [q.name for q in schema.queries]
        assert "getUser" in query_names
        assert "listUsers" in query_names
    
    def test_schema_has_default_mutations(self):
        """Test schema has default mutations"""
        class MockColumn:
            def __init__(self, name, type_str, nullable=False):
                self.name = name
                self.type = type(str(type_str), (), {})()
                self.nullable = nullable
        
        class MockTable:
            columns = [MockColumn("id", "INTEGER", nullable=False)]
        
        class MockModel:
            __table__ = MockTable()
        
        schema = create_graphql_schema_from_model(MockModel, "User")
        
        mutation_names = [m.name for m in schema.mutations]
        assert "createUser" in mutation_names
        assert "updateUser" in mutation_names
        assert "deleteUser" in mutation_names
