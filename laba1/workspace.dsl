workspace {

    model {
        user = person "Пользователь" "Пользователь мессенджера"

        messenger = softwareSystem "Мессенджер" {
            clientApp = container "Клиентское приложение" "Web/мобильные клиенты" "React Native, WebSocket"
            apiGateway = container "API Gateway" "Маршрутизация запросов" "Nginx, JWT"
            userService = container "User Service" "Регистрация и управление пользователями" "Python, FastAPI, SQLAlchemy" {
                description "Поиск пользователей через SQL-запросы к PostgreSQL"
            }
            chatService = container "Chat Service" "Создание чатов (PtP/групповых)" "Python, FastAPI, RabbitMQ"
            messageService = container "Message Service" "Отправка сообщений" "Python, WebSocket, RabbitMQ"
            database = container "Database" "Хранение данных" "PostgreSQL"

            user -> clientApp "Отправка сообщений, создание чатов"
            clientApp -> apiGateway "API запросы" "HTTPS/WebSocket"
            apiGateway -> userService "POST /users, GET /users/search" "HTTP"
            apiGateway -> chatService "POST /chats/group" "HTTP"
            apiGateway -> messageService "POST /messages" "HTTP"
            
            userService -> database "CRUD и поиск пользователей" "SQLAlchemy"
            chatService -> database "Сохранение чатов" "SQLAlchemy"
            chatService -> messageService "Уведомление о чате" "RabbitMQ"
            messageService -> database "Сохранение сообщений" "SQLAlchemy"
            messageService -> clientApp "Push-уведомления" "WebSocket"
        }
    }

    views {
        systemContext messenger {
            include user messenger
            autolayout
        }

        container messenger {
            include user clientApp apiGateway userService chatService messageService database
            autolayout
        }

        dynamic messenger "create_group_chat" "Создание группового чата" {
            user -> clientApp "1. Запрос на создание чата"
            clientApp -> apiGateway "2. POST /chats/group"
            apiGateway -> chatService "3. Создать чат"
            chatService -> database "4. Сохранить групповой чат"
            chatService -> messageService "5. Уведомить участников"
            messageService -> clientApp "6. Рассылка уведомлений"
            autolayout
        }

        theme default
    }
}
