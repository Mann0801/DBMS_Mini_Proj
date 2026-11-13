// =====================================================================
// CampusEats NoSQL part (Mann): MongoDB database "campuseats",
// collection "menu_details".
//
// MariaDB keeps the fixed, relational data (price, stock, orders).
// MongoDB keeps the flexible extra info about each dish. Different dishes
// need different fields (a drink has "served", a dessert has "sugar_free",
// a meal has "portion"), which in SQL would mean many mostly-NULL columns.
//
// Each document's _id is the dish's menu_items.item_id in MariaDB.
//
// Run with database/mongo/setup.sh (re-running resets the collection).
// =====================================================================

db = db.getSiblingDB("campuseats");

db.menu_details.drop();

// ---- 1. create the collection with a JSON-schema validator ----
db.createCollection("menu_details", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["_id", "dietary", "spice_level", "allergens"],
      properties: {
        _id:         { bsonType: "int", minimum: 1, description: "menu_items.item_id in MariaDB" },
        dietary:     { enum: ["veg", "vegan", "egg", "non-veg"] },
        spice_level: { bsonType: "int", minimum: 0, maximum: 3 },
        allergens:   { bsonType: "array", items: { bsonType: "string" } },
        tags:        { bsonType: "array", items: { bsonType: "string" } },
        calories:    { bsonType: ["int", "null"], minimum: 0 },
        special:     {
          bsonType: ["object", "null"],
          required: ["note"],
          properties: { note: { bsonType: "string" } },
        },
      },
      additionalProperties: true,   // other fields allowed: that's the point
    },
  },
  validationAction: "error",
});

// ---- 2. indexes ----
db.menu_details.createIndex({ dietary: 1 });
db.menu_details.createIndex({ allergens: 1 });              // multikey index (array)
db.menu_details.createIndex({ tags: 1 });
db.menu_details.createIndex({ spice_level: 1, dietary: 1 }); // compound index

print("Created collection menu_details with indexes: " +
      db.menu_details.getIndexes().map((i) => i.name).join(", "));
