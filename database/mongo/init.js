// =====================================================================
// CampusEats NoSQL part: MongoDB database "campuseats",
// collection "food_details" (Mann).
//
// MariaDB keeps the fixed, relational data (price, category, orders).
// MongoDB keeps the flexible extra info about each dish. Different dishes
// need different fields (a drink has "served", a dessert has "sugar_free",
// a meal has "portion"), which would mean many NULL columns in SQL.
//
// Each document's _id is the dish's food_items.id in MariaDB.
//
// Run (re-running resets the collection):
//   podman exec -i campuseats-mongo mongosh campuseats < database/mongo/init.js
// =====================================================================

db = db.getSiblingDB("campuseats");

db.food_details.drop();

// ---- create the collection with a JSON-schema validator ----
db.createCollection("food_details", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["_id", "dietary", "spice_level", "allergens"],
      properties: {
        _id:         { bsonType: "int", minimum: 1, description: "food_items.id in MariaDB" },
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
      // other fields are allowed: that flexibility is the point
      additionalProperties: true,
    },
  },
  validationAction: "error",
});

// ---- indexes ----
db.food_details.createIndex({ dietary: 1 });
db.food_details.createIndex({ allergens: 1 });          // multikey index on an array
db.food_details.createIndex({ tags: 1 });
db.food_details.createIndex({ spice_level: 1, dietary: 1 });

// ---- sample documents (ids match database/seed.sql) ----
const now = new Date();
db.food_details.insertMany([
  { _id: NumberInt(1),  dietary: "veg",   spice_level: NumberInt(2), allergens: ["gluten"],
    tags: ["bestseller", "fried"], calories: NumberInt(260), updated_at: now },
  { _id: NumberInt(2),  dietary: "veg",   spice_level: NumberInt(1), allergens: ["gluten", "dairy"],
    tags: ["baked"], calories: NumberInt(280), updated_at: now },
  { _id: NumberInt(3),  dietary: "vegan", spice_level: NumberInt(2), allergens: [],
    tags: ["fried", "street food"], calories: NumberInt(220), updated_at: now },
  { _id: NumberInt(4),  dietary: "veg",   spice_level: NumberInt(1), allergens: ["gluten", "dairy"],
    tags: ["filling", "bestseller"], calories: NumberInt(650), portion: "full plate",
    includes: ["rice", "dal", "sabzi", "2 roti", "salad"], updated_at: now },
  { _id: NumberInt(5),  dietary: "vegan", spice_level: NumberInt(2), allergens: [],
    tags: ["protein rich", "filling"], calories: NumberInt(540), portion: "full plate", updated_at: now },
  { _id: NumberInt(6),  dietary: "veg",   spice_level: NumberInt(3), allergens: ["dairy"],
    tags: ["chef special"], calories: NumberInt(720), portion: "full plate",
    special: { note: "Extra raita free today", until: "2026-11-30" }, updated_at: now },
  { _id: NumberInt(7),  dietary: "vegan", spice_level: NumberInt(0), allergens: [],
    tags: ["light", "comfort food"], calories: NumberInt(430), updated_at: now },
  { _id: NumberInt(8),  dietary: "veg",   spice_level: NumberInt(2), allergens: ["gluten", "dairy"],
    tags: ["bestseller", "protein rich"], calories: NumberInt(480), updated_at: now },
  { _id: NumberInt(9),  dietary: "veg",   spice_level: NumberInt(2), allergens: ["gluten"],
    tags: ["street food"], calories: NumberInt(390), updated_at: now },
  { _id: NumberInt(10), dietary: "veg",   spice_level: NumberInt(1), allergens: ["gluten", "dairy"],
    tags: ["grilled"], calories: NumberInt(410), cheese: "cheddar", updated_at: now },
  { _id: NumberInt(11), dietary: "veg",   spice_level: NumberInt(0), allergens: ["dairy"],
    tags: ["hot drink"], calories: NumberInt(120), served: "hot", cup_ml: NumberInt(150), updated_at: now },
  { _id: NumberInt(12), dietary: "veg",   spice_level: NumberInt(0), allergens: ["dairy"],
    tags: ["cold drink"], calories: NumberInt(210), served: "cold", caffeine: true, updated_at: now },
  { _id: NumberInt(13), dietary: "veg",   spice_level: NumberInt(0), allergens: ["dairy"],
    tags: ["cold drink", "seasonal"], calories: NumberInt(240), served: "cold",
    special: { note: "Made with Alphonso mangoes" }, updated_at: now },
  { _id: NumberInt(14), dietary: "veg",   spice_level: NumberInt(0), allergens: ["dairy", "gluten"],
    tags: ["sweet"], calories: NumberInt(300), sugar_free: false, pieces: NumberInt(2), updated_at: now },
  { _id: NumberInt(15), dietary: "egg",   spice_level: NumberInt(0), allergens: ["gluten", "dairy", "egg", "nuts"],
    tags: ["sweet", "bestseller"], calories: NumberInt(380), sugar_free: false, updated_at: now },
]);

print("food_details documents: " + db.food_details.countDocuments());
printjson(db.food_details.getIndexes().map((i) => i.name));
