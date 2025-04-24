db = db.getSiblingDB('chatdb');

// Создание коллекций
db.createCollection('chats');
db.createCollection('messages');

// Создание индексов
db.chats.createIndex({ "chat_id": 1 }, { unique: true });
db.chats.createIndex({ "participants": 1 });
db.messages.createIndex({ "chat_id": 1, "timestamp": -1 });

// Тестовые данные
db.chats.insertOne({
    chat_id: 1,
    name: "General Chat",
    creator_id: 1,
    participants: [1],
    created_at: new Date()
});

db.messages.insertOne({
    chat_id: 1,
    sender_id: 1,
    text: "Welcome to MongoDB chat!",
    timestamp: new Date()
});