workspace {

    model {
        user = person "User" "Пользователь системы"
        
        messenger = softwareSystem "Messenger" "Система обмена сообщениями" {
            apiGateway = container "API Gateway" "Маршрутизация запросов" "Nginx, JWT"
            
            userService = container "User Service" {
                description "Управление пользователями и аутентификация"
                technology "Python FastAPI, JWT"
            }
            
            chatService = container "Chat Service" {
                description "Управление чатами и сообщениями"
                technology "Python FastAPI"
            }
        }

        # Взаимодействия
        user -> apiGateway "Отправка запросов" "HTTP"
        
        apiGateway -> userService "POST /token \n GET /users/{id}" "HTTP"
        
        apiGateway -> chatService "POST /chats\nPOST /chats/{id}/participants\nPOST /chats/{id}/messages\nGET /chats/{id}" "HTTP"
        
        chatService -> userService "Проверка пользователей" "HTTP"
    }

    views {
        systemContext messenger {
            include user messenger
            autolayout
        }

        container messenger {
            include user apiGateway userService chatService
            autolayout
        }

        theme default
    }
}