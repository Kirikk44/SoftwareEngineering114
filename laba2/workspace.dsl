workspace {
    model {
        user = person "Пользователь"

        messenger = softwareSystem "Мессенджер" {
            userService = container "User Service" "FastAPI, JWT, In-Memory" {
                description "Регистрация, аутентификация, управление пользователями"
            }
            
            chatService = container "Chat Service" "FastAPI, In-Memory" {
                description "Создание и управление чатами"
            }
            
            user -> userService "Регистрация/логин"
            user -> chatService "Работа с чатами"
            userService -> chatService "Валидация токена"
        }
    }
    
    views {
        container messenger {
            include user userService chatService
            autolayout
        }
    }
}