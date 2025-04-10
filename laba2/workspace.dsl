workspace {

    model {
        user = person "User" "Пользователь системы"
        
        messenger = softwareSystem "Messenger" "Система обмена сообщениями" {
            userService = container "User Service" {
                description "Управление пользователями и аутентификация"
                technology "Python FastAPI, JWT"
            }
            
            chatService = container "Chat Service" {
                description "Управление чатами и сообщениями"
                technology "Python FastAPI"
            }

            postgres = container "PostgreSQL" {
                description "Реляционная база данных"
                technology "PostgreSQL"
            }
        }

        user -> userService "POST /token\nGET /users/{id}" "HTTP"
        
        user -> chatService "POST /chats\nPOST /chats/{id}/participants\nPOST /chats/{id}/messages\nGET /chats/{id}" "HTTP"
        
        userService -> postgres """CRUD операции\nХранение пользователей" "SQL"
        
        chatService -> userService "Проверка пользователей" "HTTP"
    }

    views {
        systemContext messenger {
            include user messenger
            autolayout
        }

        container messenger {
            include user userService chatService postgres
            autolayout
        }

        dynamic messenger "create_user" "Создание пользователя"{
            user -> userService "1. POST /users"
            userService -> postgres "3. Сохранение в БД"
            autolayout
        }

        theme default
    }
}