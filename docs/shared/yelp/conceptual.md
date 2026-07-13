# Entity Connections

```mermaid
classDiagram
    direction LR

    class User {
        
    }

    class Business {
       
    }

    class Review {
       
    }

    class Tip {
        
    }

    class Checkin {
        
    }

    Review --> User : user_id
    Review --> Business : business_id
    Tip --> User : user_id
    Tip --> Business : business_id
    Checkin --> Business : business_id
    User --> User : friends
```
