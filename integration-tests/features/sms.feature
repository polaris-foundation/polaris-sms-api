Feature: Article management
    As a clinician
    I want to send SMS messages to the patients
    So that patients can be informed about their condition


    Scenario: New message is sent
        Given an SMS message is sent
        Then the message can be seen in all messages
        And the message can be retrieved by its uuid
        And the message matches that previously created

    Scenario: Message is deleted
        Given an SMS message is sent
        When the message is deleted
        Then the message can not be seen in all messages
        And the message can not be retrieved by its uuid

    Scenario: Message callback is received
        Given an SMS message is sent
        When a message callback is received with status "delivered"
        Then the message status is updated accordingly
        And the message body has been marked as redacted

    Scenario: Bulk update messages' status
        Given an SMS message is sent
        And a message callback is received with status "queued"
        When a bulk update call is received
        Then the status of all incomplete messages is updated

    Scenario: Bulk update messages' redaction
        Given an SMS message has been delivered but not redacted
        When a bulk update call is received
        Then all complete message have been marked as redacted

    Scenario: Message counts
        Given an initial message count is taken
        And an SMS message is sent
        And a message callback is received with status "delivered"
        And another SMS message is sent
        And a message callback is received with status "queued"
        When a final message count is taken
        Then there is 1 new message with status "delivered" counted
        And there is 1 new message with status "queued" counted
