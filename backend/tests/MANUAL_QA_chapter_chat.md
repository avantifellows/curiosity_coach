# Manual QA: KB-scoped chapter chat

1. Subscribe to a project on the student dashboard, then use **Go to chat** with that project selected.
2. Confirm a conversation is created and the first assistant message loads.
3. In the database, confirm `progress.status` is `ongoing` and `progress.conversation_id` matches the new `conversations.id` for the resolved foundational unit.
4. Mark all progress rows for that kb source as `done` (SQL or admin), open **Go to chat** again for the same project: you should see **You have finished this chapter** and no new conversation.
5. Open chat with `project_source_id` for a kb source you never subscribed to: expect an error message about subscribing first.
