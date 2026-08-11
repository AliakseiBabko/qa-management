# Performance Environment Discovery

Scope: deriving performance-testing scope from live infrastructure,
JMeter/GitLab evidence, source repositories, and project knowledge. Use this
when the user needs a service/script matrix, a deployed-service inventory, or
an answer to "what physical blocks should performance tests target?"

## Source-Of-Truth Order

For performance testing, the primary unit is the deployed physical block, not
the planning-sheet row. Work in this order:

1. **Live deployed inventory** - Kubernetes, Prometheus, service discovery,
   ingress, or the platform's own runtime inventory. This decides whether a
   target exists in the environment.
2. **CI/JMeter evidence** - job metadata, pipeline variables, JMX files,
   result artifacts, Pushgateway/Prometheus labels, and runner context. This
   decides what has already run and where the load generator actually sent
   traffic.
3. **Source repositories** - controllers, generated API docs, consumers,
   plugins, table-template runtimes, and deployment manifests. This explains
   purpose, endpoints, auth shape, event boundaries, and which logical
   submodules live inside a physical block.
4. **Project documents and developer statements** - use them to explain
   intent and resolve ambiguous ownership. Treat them as secondary to live
   deployment evidence for "is this testable here now?"

If these sources disagree, keep the contradiction visible in Open Questions
and state the test-planning consequence.

## Terminology

Use these labels consistently in knowledge-base and performance-plan output:

- **Physical service** - independently deployed runtime with its own pod,
  service, process, or externally routable endpoint. This is usually a
  top-level performance-test target.
- **Runtime host** - a generic service that hosts multiple logical modules
  or table groups. Performance coverage belongs to the runtime plus selected
  workflows inside it, not to a fake service per submodule.
- **Table group** - a deployed table-template runtime/group. Treat it as a
  physical runtime slice when it has its own deployment/service, but do not
  confuse it with a standalone business microservice.
- **Plugin/submodule** - logical code loaded into a service/runtime. It can
  justify a scenario, but it is not automatically an independent load-test
  target.
- **Library** - embedded code with no process or endpoint of its own. Test it
  through a concrete host service/table/workflow.
- **Event-driven service** - physical service whose main workload is a
  message/event/queue flow rather than a REST endpoint. Do not force it into
  a REST JMeter script; design the script around the trigger and observable
  completion signal.

## Discovery Checklist

For each candidate service or module row:

1. Confirm deployment exists and record environment, namespace, deployment
   name, replica count, pod scrape status, and service/route identity.
2. Confirm how it is reachable from the load generator: ingress route,
   cluster DNS, service mesh, direct ClusterIP, or not reachable.
3. Probe only safe read-only endpoints first: health, API docs, metadata,
   or a documented idempotent read. Record exact status codes, because
   `200`, `401`, `403`, and `404` mean different script work.
4. Read source to classify it as REST, runtime host/table group, plugin,
   library, or event-driven service.
5. Map logical submodules to the physical block that actually executes them.
6. Check existing JMeter/Gatling/k6 scripts and previous result artifacts.
   Separate plumbing/smoke scripts from business-workload scripts.
7. Record blockers as concrete Open Questions: missing deployment, route
   owner unknown, auth token missing, artifact retrieval broken, async
   completion signal unknown, or test data unavailable.

## Service/Script Matrix Fields

Use this shape when the output is a performance test scope table:

- `Physical block`
- `Runtime type` (`REST service`, `runtime host/table group`,
  `event-driven service`, `frontend`, `library via host`, `not deployed`)
- `Included submodules/plugins/table groups`
- `Evidence` (`deployment`, `service`, `route`, `job`, `repo`, `source doc`)
- `Reachability from load generator`
- `Existing script/result coverage`
- `Scenario to implement`
- `Auth/test-data dependency`
- `Observability dependency`
- `Status` (`ready`, `needs auth`, `needs route`, `needs test data`,
  `async design needed`, `not deployed`, `out of scope`)

## Knowledge-Base Update Rule

When a live investigation changes performance scope, update durable sections
instead of only answering in chat:

- `System/Architecture` for physical service and runtime-host inventory.
- `Performance-Critical Scenarios` for what should actually be scripted.
- `Known Constraints` for environment, runner, observability, route, or
  artifact limitations.
- `Open Questions` for unresolved access, ownership, async-signal, or
  deployment gaps.
- `Change Log` with a one-line pointer only.

Do not store IP addresses, hostnames, runner names, or project paths in this
public repo. Those details belong in the project's Drive-hosted knowledge
documents.
