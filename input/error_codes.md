# Error code reference

This reference lists internal error identifiers. Each entry uses the same
format so that the identifier is the most useful exact-match signal.

## ERR-1001
Meaning: the request could not be accepted. Condition: the submitted payload
did not pass the initial validation check. Response: review the payload and
submit it again after correcting the invalid field. Owner: Platform Support.
The code identifies the validation condition, not a permission failure, and
the response should preserve the original request identifier for follow-up.

## ERR-1142
Meaning: the request timed out. Condition: the service did not receive a
complete response before the configured waiting period. Response: retry once
after checking service health. Owner: Runtime Operations. The code identifies
the timeout condition, not a network authorization failure, and the response
should preserve the original request identifier for follow-up.

## ERR-2077
Meaning: the account is not ready. Condition: required account setup has not
finished. Response: wait for setup to complete and retry the operation. Owner:
Identity Support. The code identifies the account condition, not a permission
failure, and the response should preserve the original request identifier.

## ERR-3188
Meaning: the document could not be read. Condition: the source content was
missing or could not be parsed. Response: verify the source path and upload the
document again. Owner: Knowledge Operations. The code identifies the document
condition, not a model failure, and the response should preserve the source
identifier for follow-up.

## ERR-4026
Meaning: the index is unavailable. Condition: the search index did not answer
the lookup. Response: retry after index health is restored. Owner: Search
Operations. The code identifies the index condition, not a document permission
failure, and the response should preserve the original query identifier.

## ERR-4821
Meaning: the requested record was not found. Condition: no stored record
matched the supplied record identifier. Response: verify the identifier and
retry the lookup. Owner: Data Support. The code identifies the missing-record
condition, not an authentication failure, and the response should preserve
the original query identifier for follow-up.

## ERR-5173
Meaning: the configuration is incomplete. Condition: a required setting was
not supplied to the service. Response: add the missing setting and restart the
service. Owner: Platform Support. The code identifies the configuration
condition, not a runtime capacity failure, and the response should preserve
the deployment identifier for follow-up.

## ERR-6002
Meaning: the source is stale. Condition: a document version is older than the
version recorded by the source owner. Response: refresh the document and run
indexing again. Owner: Knowledge Operations. The code identifies the stale
source condition, not a vector generation failure, and the response should
preserve the source identifier for follow-up.

## ERR-7315
Meaning: the policy check failed. Condition: the operation did not satisfy a
required policy rule. Response: review the policy result and request approval
when appropriate. Owner: Governance Support. The code identifies the policy
condition, not a transport failure, and the response should preserve the
operation identifier for follow-up.

## ERR-8044
Meaning: the response was incomplete. Condition: a required output field was
not returned by the downstream service. Response: retry the operation and
inspect the downstream logs if it continues. Owner: Runtime Operations. The
code identifies the output condition, not a user-input validation failure.

## ERR-9140
Meaning: the operation was rate limited. Condition: the service received more
requests than the configured allowance. Response: wait and retry with the
recommended backoff. Owner: Platform Support. The code identifies the rate
condition, not a permission failure, and the response should preserve the
original request identifier for follow-up.

## ERR-1026
Meaning: the connection was closed. Condition: the remote service ended the
connection before the operation completed. Response: retry after checking
network health. Owner: Runtime Operations. The code identifies the connection
condition, not a source-content failure, and the response should preserve the
request identifier for follow-up.

## ERR-1189
Meaning: the token is expired. Condition: the supplied access token passed its
validity period. Response: obtain a new token and retry the operation. Owner:
Identity Support. The code identifies the token condition, not a role mismatch,
and the response should preserve the request identifier for follow-up.

## ERR-2264
Meaning: the queue is full. Condition: the service could not accept another
work item at the current queue limit. Response: wait for capacity and retry.
Owner: Runtime Operations. The code identifies the queue condition, not a
document parsing failure, and the response should preserve the work identifier.

## ERR-3370
Meaning: the schema is incompatible. Condition: the stored payload uses a
schema version unsupported by the current service. Response: migrate the
payload before retrying. Owner: Data Support. The code identifies the schema
condition, not a network failure, and the response should preserve the record
identifier for follow-up.

## ERR-4492
Meaning: the file is too large. Condition: the uploaded source exceeds the
configured size limit. Response: reduce the file size and upload it again.
Owner: Knowledge Operations. The code identifies the size condition, not a
content permission failure, and the response should preserve the source path.

## ERR-5631
Meaning: the lock is held. Condition: another operation currently owns the
required resource lock. Response: wait for the owner to finish and retry.
Owner: Platform Support. The code identifies the lock condition, not a timeout
from the downstream service, and the response should preserve the operation ID.

## ERR-6778
Meaning: the dependency is unavailable. Condition: a required internal service
did not pass its health check. Response: restore dependency health and retry.
Owner: Runtime Operations. The code identifies the dependency condition, not a
user permission failure, and the response should preserve the request ID.

## ERR-7890
Meaning: the result is ambiguous. Condition: multiple records matched the
provided lookup value. Response: use a more specific identifier and retry.
Owner: Data Support. The code identifies the ambiguity condition, not a missing
record, and the response should preserve the original query identifier.

## ERR-8952
Meaning: the operation was cancelled. Condition: the caller or system stopped
the operation before completion. Response: confirm the desired state and
start a new operation. Owner: Platform Support. The code identifies the
cancellation condition, not an authorization failure, and the response should
preserve the operation identifier.

## ERR-9361
Meaning: the output was rejected. Condition: a downstream validator rejected
the generated result. Response: inspect the validation detail and retry after
correction. Owner: Governance Support. The code identifies the output condition,
not an input transport failure, and the response should preserve the request ID.

## ERR-1475
Meaning: the source was duplicated. Condition: the same source identifier was
submitted more than once. Response: keep the newest source and remove the
duplicate submission. Owner: Knowledge Operations. The code identifies the
duplicate condition, not a stale-source warning, and the response should
preserve the source identifier.

## ERR-2598
Meaning: the request was malformed. Condition: the request structure did not
match the endpoint contract. Response: compare the request with the API schema
and submit it again. Owner: Platform Support. The code identifies the request
condition, not a policy failure, and the response should preserve the request ID.

## ERR-3642
Meaning: the model was unavailable. Condition: the local model endpoint did
not respond to the generation request. Response: restore model health and
retry. Owner: Runtime Operations. The code identifies the model condition, not
a vector mismatch, and the response should preserve the generation identifier.

## ERR-4760
Meaning: the vector was invalid. Condition: an embedding did not match the
configured dimension. Response: regenerate the embedding with the configured
model. Owner: Search Operations. The code identifies the vector condition, not
a full-text query failure, and the response should preserve the chunk ID.

## ERR-5814
Meaning: the index was outdated. Condition: stored search data did not include
the newest source version. Response: run the indexing job and retry the search.
Owner: Search Operations. The code identifies the index condition, not a
document-read failure, and the response should preserve the source ID.

## ERR-6937
Meaning: the metadata was invalid. Condition: a metadata value did not match
the accepted type. Response: correct the metadata and submit it again. Owner:
Data Support. The code identifies the metadata condition, not an authentication
failure, and the response should preserve the document identifier.

## ERR-7086
Meaning: the operation exceeded its budget. Condition: the operation consumed
more time or resources than allowed. Response: reduce the request scope and
retry. Owner: Platform Support. The code identifies the budget condition, not a
rate-limit response, and the response should preserve the request identifier.

## ERR-8193
Meaning: the result was filtered. Condition: the result did not meet the
configured retrieval threshold. Response: review the query and threshold before
retrying. Owner: Search Operations. The code identifies the filter condition,
not a missing database record, and the response should preserve the query ID.

## ERR-9274
Meaning: the migration is pending. Condition: the database has not applied a
required idempotent migration. Response: apply the migration and restart the
application. Owner: Data Support. The code identifies the migration condition,
not a connection failure, and the response should preserve the deployment ID.

## ERR-1359
Meaning: the source owner is unknown. Condition: no owner matched the source
metadata. Response: assign an owner before publishing the source. Owner:
Governance Support. The code identifies the ownership condition, not a source
read failure, and the response should preserve the source identifier.

## ERR-2480
Meaning: the request is forbidden. Condition: the caller lacks the required
permission for the operation. Response: request access from the resource owner.
Owner: Identity Support. The code identifies the permission condition, not an
expired token, and the response should preserve the request identifier.

## ERR-3567
Meaning: the retry limit was reached. Condition: repeated attempts did not
complete within the configured retry count. Response: inspect the first failure
and start a controlled retry. Owner: Runtime Operations. The code identifies the
retry condition, not a rate-limit response, and the response should preserve
the operation identifier.

## ERR-4673
Meaning: the query had no terms. Condition: filtering removed every token from
the submitted question. Response: provide a question containing searchable
terms. Owner: Search Operations. The code identifies the empty-query condition,
not a database outage, and the response should preserve the query identifier.

## ERR-5726
Meaning: the content was empty. Condition: the source contained no indexable
text after preprocessing. Response: add content and upload the source again.
Owner: Knowledge Operations. The code identifies the empty-content condition,
not an invalid vector, and the response should preserve the source identifier.

## ERR-6841
Meaning: the result was truncated. Condition: the response exceeded the context
budget and was shortened. Response: narrow the query or increase the approved
context limit. Owner: Runtime Operations. The code identifies the context
condition, not a missing source, and the response should preserve the request ID.
