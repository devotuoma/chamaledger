# LinkedIn: SQLite hid a data leak

My tests passed on SQLite. Postgres showed a privacy bug.

I had set hide_parameters=True so customer values stay out of error messages. On Postgres, the phone number still appeared, because the database quotes the duplicate key in its own error text.

The fix was layered: check for duplicates up front, scrub logs in the app, and scrub spans in the collector.

Lesson: run integration tests on the database you run in production.

The test that checks it: https://github.com/devotuoma/chamaledger/blob/main/backend/tests/integration/test_no_customer_data.py

#Privacy #Testing #Postgres
