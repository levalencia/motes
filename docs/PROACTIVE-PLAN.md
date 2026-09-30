# Proactive Intelligence — Implementation Plan

## What Dots Does (from video + research)

1. **Background scanning**: When user is idle, scans Gmail, Calendar, etc. (READ-ONLY)
2. **Pattern learning**: Tracks what user asks frequently, at what times
3. **Push notifications**: "You have overlapping meetings", "Important email from boss"
4. **Suggested actions**: "Want me to find parking?" "Should I draft a reply?"
5. **Compound memory**: Remembers preferences, adapts over time

## Implementation for Motes

### Phase 1: Pattern Learning (from interactions)

Every time the user chats, we extract and save:
- **Time patterns**: "user asks for weather at 8am", "checks emails at 9am"
- **Topic patterns**: "user frequently asks about calendar", "interested in AI news"
- **People patterns**: "user emails Diana often", "meetings with John are important"

Store in a `user_patterns` table:
- pattern_type: "time_action", "topic_interest", "person_importance"
- pattern_data: JSON with frequency, last_seen, confidence score
- agent_id: scoped per agent

### Phase 2: Background Monitoring (proactive scan)

A background worker that runs every N minutes:
1. Check Gmail for new unread emails (if connected)
2. Check Calendar for upcoming events/conflicts
3. Compare against learned patterns
4. Generate notifications when something matches

### Phase 3: Notification System

- WebSocket or SSE push to frontend
- Notification bell icon in nav bar
- Toast notifications for urgent items
- Notification history/inbox

### Phase 4: Suggested Actions

Based on patterns + current context:
- Morning: "Good morning! You have 3 meetings today, 2 unread emails from Diana"
- Calendar conflict detected: "Your 2pm and 2:30pm meetings overlap"
- New email from important contact: "Email from Diana about Q4 report"
