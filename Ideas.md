# Curiosity Coach - Architecture Ideas

## Option 1: Lambda + SQS + FastAPI (Recommended)

```
┌─────────────┐    ┌─────────┐    ┌─────────────┐    ┌───────────┐
│ React       │───►│ FastAPI │───►│ SQS Queue   │───►│ Lambda    │
│ Frontend    │◄───│ Backend │◄───│             │◄───│ (LLM)     │
└─────────────┘    └─────────┘    └─────────────┘    └───────────┘
                        │                                  │
                        ▼                                  ▼
                   ┌─────────┐                      ┌─────────────┐
                   │ Postgres│                      │ LLM API     │
                   │ Database│                      │ (OpenAI/etc)│
                   └─────────┘                      └─────────────┘
```

**Pros:**
- Replaces Flask with FastAPI (async, better performance)
- Lambda handles LLM processing asynchronously
- SQS decouples request/response cycle
- Scalable and cost-effective

**Cons:**
- More complex architecture
- Requires handling asynchronous responses

## Option 2: Container-Based with Kubernetes

```
┌─────────────┐    ┌────────────────────────────────────┐
│ React       │    │ Kubernetes Cluster                 │
│ Frontend    │    │  ┌──────────┐       ┌──────────┐   │
│             │◄──►│  │ API      │◄─────►│ LLM      │   │
└─────────────┘    │  │ Service  │       │ Service  │   │
                   │  └──────────┘       └──────────┘   │
                   │        │                │          │
                   │        ▼                ▼          │
                   │  ┌──────────┐    ┌─────────────┐   │
                   │  │ Database │    │ Redis Cache │   │
                   │  └──────────┘    └─────────────┘   │
                   └────────────────────────────────────┘
```

**Pros:**
- Highly scalable and resilient
- Good isolation between components
- Better control over resource allocation
- Easier to implement complex workflows

**Cons:**
- Higher operational complexity
- More expensive than serverless
- Requires DevOps expertise

## Option 3: Hybrid Flask/Celery Architecture

```
┌─────────────┐    ┌─────────┐    ┌─────────────┐    ┌───────────┐
│ React       │───►│ Flask   │───►│ Redis/RabbitMQ│──►│ Celery    │
│ Frontend    │◄───│ Backend │◄───│             │◄───│ Workers   │
└─────────────┘    └─────────┘    └─────────────┘    └───────────┘
                        │                                  │
                        ▼                                  ▼
                   ┌─────────┐                      ┌─────────────┐
                   │ Postgres│                      │ LLM API     │
                   │ Database│                      │ (OpenAI/etc)│
                   └─────────┘                      └─────────────┘
```

**Pros:**
- Keeps your Flask backend but adds async capability
- Easy to implement with your existing code
- Good for complex processing pipelines
- Lower learning curve than containerization

**Cons:**
- Still needs a server running 24/7
- More complex to deploy than pure serverless

## Recommendation: Option 1 (Lambda + SQS + FastAPI)

Your instinct to use Lambda is spot on. Here's why this approach makes sense:

1. **Cost Efficiency**: 
   - You only pay for actual LLM processing time
   - Lambda scales to zero when not in use

2. **Performance**: 
   - FastAPI is ~3x faster than Flask and supports async natively
   - LLM calls won't block your API server

3. **Simplicity**:
   - Lambda handles scaling automatically
   - SQS provides built-in retry and error handling

## Implementation Details:

1. **FastAPI Backend**:
   ```python
   # Async message handling with FastAPI
   @app.post("/api/messages")
   async def send_message(message: MessageSchema, user = Depends(get_current_user)):
       # Save user message
       db_message = save_message(user.id, message.content, is_user=True)
       
       # Queue for LLM processing
       await queue_service.send_message(user.id, message.content, db_message["id"])
       
       # Return immediately with acknowledgment
       return {"success": True, "message": db_message}
   ```

2. **Lambda Function**:
   ```python
   def lambda_handler(event, context):
       for record in event['Records']:
           # Process message with LLM
           payload = json.loads(record['body'])
           user_id = payload['user_id']
           content = payload['message_content']
           
           # Call LLM API
           llm_response = call_llm_api(content)
           
           # Save response to database
           save_message_to_db(user_id, llm_response, is_user=False)
   ```

3. **Frontend Polling**:
   ```typescript
   // Poll for new messages after sending
   const pollForResponse = async () => {
     const interval = setInterval(async () => {
       try {
         const history = await getChatHistory();
         if (history.messages.length > messages.length) {
           setMessages(history.messages);
           clearInterval(interval);
         }
       } catch (err) {
         console.error(err);
       }
     }, 1000);
     
     // Stop polling after 30 seconds
     setTimeout(() => clearInterval(interval), 30000);
   };
   ```

## Advanced Features to Consider:

1. **WebSockets for Real-time Updates**:
   - FastAPI has built-in WebSocket support
   - Lambda can trigger a WebSocket broadcast when LLM response is ready

2. **Caching Layer**:
   - Add Redis/DynamoDB for caching common LLM responses
   - Reduce costs and improve response times

3. **LLM Implementation Options**:
   - API-based: OpenAI, Claude, etc.
   - Self-hosted: Llama, Falcon, Mistral (on dedicated EC2/Lambda)
   - Managed: Bedrock, SageMaker

4. **Progressive Enhancement**:
   - Start with the Lambda architecture
   - Add more complex features as needed
   - Easy to evolve without major rewrites

This architecture gives you the best of both worlds: a responsive API for user interactions and scalable, efficient processing for the computationally expensive LLM operations.

## Multi-Purpose Lambda Architecture with Model Routing

Adding task-specific model selection via SQS is an excellent enhancement. Here's how to structure it:

```
┌─────────────┐    ┌─────────┐    ┌─────────────┐    ┌─────────────────────┐
│ React       │───►│ FastAPI │───►│ SQS Queue   │───►│ Lambda Router       │
│ Frontend    │◄───│ Backend │◄───│             │◄───│                     │
└─────────────┘    └─────────┘    └─────────────┘    │  ┌───────────────-┐ │
                                                     │  │ Curiosity Model| │
                                                     │  └───────────────-┘ │
                                                     │                     │
                                                     │  ┌───────────────┐  │
                                                     │  │ Other things  │  |
                                                     │  └───────────────┘  │
                                                     │                     │
                                                     │  ┌───────────────┐  │
                                                     │  │ etc etc etc   │  │
                                                     │  └───────────────┘  │
                                                     └─────────────────────┘
```

### Implementation Approach:

1. **Enhanced SQS Message Schema**:
   ```json
   {
     "user_id": "user123",
     "message_id": "db_message_789",
     "task_type": "test_generation",
     "conversation_id": "conv_456"
   }
   ```

2. **FastAPI Endpoint Variants**:
   ```python
   @app.post("/api/chat")
   async def send_chat_message(message: MessageSchema, user = Depends(get_current_user)):
       return await queue_message(user.id, message.content, "chat")
   
   @app.post("/api/generate_test")
   async def generate_test(request: TestRequestSchema, user = Depends(get_current_user)):
       return await queue_message(user.id, request.content, "test_generation", 
                                 model_params={"temperature": 0.2})
   
   @app.post("/api/solve_doubt")
   async def solve_doubt(request: DoubtSchema, user = Depends(get_current_user)):
       return await queue_message(user.id, request.content, "doubt_solver")
   
   async def queue_message(user_id, content, task_type, model_params=None):
       # Save message to DB
       db_message = save_message(user_id, content, is_user=True)
       
       # Queue for processing with task type
       await queue_service.send_message(
           user_id, 
           content, 
           db_message["id"],
           task_type=task_type,
           model_params=model_params
       )
       
       return {"success": True, "message": db_message}
   ```

3. **Lambda Router Handler**:
   ```python
   def lambda_handler(event, context):
       for record in event['Records']:
           payload = json.loads(record['body'])
           
           # Extract routing information
           user_id = payload['user_id']
           content = payload['message_content']
           task_type = payload.get('task_type', 'chat')  # Default to chat
           model_params = payload.get('model_params', {})
           
           # Route to appropriate handler based on task_type
           if task_type == 'chat':
               response = handle_chat(content, model_params)
           elif task_type == 'test_generation':
               response = generate_test_content(content, model_params)
           elif task_type == 'doubt_solver':
               response = solve_student_doubt(content, model_params)
           else:
               response = {"error": f"Unknown task type: {task_type}"}
           
           # Save response to database
           save_message_to_db(user_id, response, is_user=False, 
                             task_type=task_type)
   ```

### Benefits of This Architecture:

1. **Unified Infrastructure**: Single Lambda function handles multiple tasks
2. **Model Optimization**: Select appropriate models for different tasks
   - Chat: More conversational models (Claude, GPT-4)
   - Test Generation: More structured, deterministic outputs (lower temperature)
   - Doubt Solving: Models with educational knowledge

3. **Cost Efficiency**: 
   - Use cheaper/smaller models for simpler tasks
   - Scale up to more powerful models only when needed

4. **Easy Extensibility**:
   - Add new task types without changing infrastructure
   - Experiment with different model parameters per task type

5. **Consistent Processing Pattern**:
   - All tasks follow the same async workflow
   - Unified error handling and retry logic

This approach gives you a flexible system that can grow with your product requirements while maintaining a clean architecture.

### SQS Message Schema Implementation Considerations

When implementing this enhanced SQS message schema:

1. **Keep SQS Messages Minimal**:
   - Focus on just the essential routing information
   - Core fields only:
     - `user_id`: For authentication and data association
     - `message_id`: Database reference to the original message
     - `task_type`: Router selector ("chat", "test_generation", "doubt_solver")
     - `conversation_id`: To group related messages (optional)

   ```json
   {
     "user_id": "user123",
     "message_id": "db_message_789",
     "task_type": "test_generation",
     "conversation_id": "conv_456"
   }
   ```

2. **Database-Driven Approach**:
   - Store detailed parameters and content in your database
   - Lambda retrieves full context using the `message_id`
   - Avoids redundant data in SQS messages
   - Simplifies schema evolution over time

   ```python
   def lambda_handler(event, context):
       for record in event['Records']:
           payload = json.loads(record['body'])
           
           # Get message details from database
           message_id = payload['message_id']
           message_data = get_message_from_db(message_id)
           
           # Get task-specific config from database or config store
           task_type = payload['task_type']
           task_config = get_task_config(task_type)
           
           # Process with correct handler and config
           process_message(message_data, task_type, task_config)
   ```

3. **Backend Configuration Storage**:
   - Store model parameters and task-specific settings in:
     - Database configurations
     - Environment variables
     - Parameter Store / Secrets Manager
   - Allows changing model parameters without code changes
   - Enables A/B testing different configurations

4. **Advantages of This Approach**:
   - **Simpler Message Structure**: Less error-prone, easier to validate
   - **Reduced Coupling**: Frontend only needs to specify task type, not implementation details
   - **Centralized Configuration**: Change model parameters in one place
   - **Future-Proof**: Add new parameters without changing message schema
   - **Optimal Resource Usage**: Minimizes SQS message size and processing overhead

5. **Implementation Example**:
   ```python
   # FastAPI endpoint
   @app.post("/api/message")
   async def handle_message(
       message: BaseMessageSchema, 
       user = Depends(get_current_user)
   ):
       # Save complete message details to database
       db_message = save_message_to_db(
           user_id=user.id,
           content=message.content,
           task_type=message.task_type,
           additional_params=message.params
       )
       
       # Minimal SQS message
       await queue_service.send_message({
           "user_id": user.id,
           "message_id": db_message["id"],
           "task_type": message.task_type,
           "conversation_id": message.conversation_id
       })
       
       return {"success": True, "message_id": db_message["id"]}
   ```

This leaner approach provides the right balance between flexibility and simplicity, letting your backend handle the complexity while keeping your SQS messages focused solely on routing.
