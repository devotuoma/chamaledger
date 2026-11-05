# X: what tests caught

Bugs my tests and CI caught on one project:

- FastAPI reported a route without its prefix, so my key metric would have stayed at zero
- Postgres quoted a phone number in an error
- My agent's fix was missing a Content-Type

None of these were visible on the happy path.

https://github.com/devotuoma/chamaledger
