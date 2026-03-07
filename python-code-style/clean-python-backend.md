---
name: clean-python-backend
version: 2.0.0
description: Production-grade Clean Architecture / Hexagonal Architecture / Domain-Driven Design for Python + Litestar backends beyond CRUD. Ports & adapters, DDD entities, use-case orchestration, manual dependency injection, swappable adapters, and battle-tested testing strategy.
---

# Clean Python Backend (Litestar)

## TL;DR

```
<backend-src>/
├── domain/              # Pure business rules — zero dependencies
├── application/         # Use-cases + port interfaces
│   ├── ports/           # Contracts for infrastructure
│   └── usecases/        # One folder per business operation
├── infrastructure/      # Adapters, config, DI composition
│   ├── adapters/
│   │   ├── driven/      # Outbound (DB, cache, APIs, queues)
│   │   └── driving/     # Inbound (HTTP, CLI, workers)
│   ├── composition/     # DI container
│   └── config/          # Environment (single env reader)
├── shared/              # Cross-cutting types, schemas, helpers
└── scripts/             # Entry points (minimal glue)
```

**5 Golden Rules:**

1. **Domain is pure** — no async, no I/O, no imports from outer layers
2. **Use-cases orchestrate** — one per business operation, injected with ports
3. **Ports are protocols** — named by role, never by technology
4. **Adapters translate** — no business logic, just map between tech and domain
5. **Manual DI** — one `container.py` wires everything, no framework magic

---

## Instructions for Claude

**When to apply this skill:** The user's backend has business logic beyond CRUD — state machines, multiple swappable providers, domain rules with invariants, async pipelines, or billing/credits logic.

**How to detect:** Look for existing `domain/`, `application/`, `infrastructure/` folders, or port protocols. If the project already follows this pattern, continue it. If the user asks to create a new feature in a project using this architecture, follow the Delivery Checklist (Section 9).

**When NOT to apply:** Simple REST APIs that read/write a database with no domain logic. Use a flat controller/service/repository pattern instead.

**Applying the skill:**
- Place new business rules in `domain/<module>/`
- Create port protocols in `application/ports/<category>/`
- Create use-cases as classes with an `async execute(...)` method
- Wire in `infrastructure/composition/container.py`
- Test use-cases with in-memory adapters, never with `MagicMock()` on ports

---

## When to Use This Skill

Use this architecture when your backend has **at least one** of:

- Business logic with rules, state machines, or invariants (not just pass-through CRUD)
- Multiple external providers that may change (AI engines, payment, transcription, storage)
- Domain concepts worth protecting (billing, credits, subscriptions, order lifecycle)
- Async processing pipelines (queues, workers, multi-step workflows)

**Don't use this** for simple REST APIs that just read/write a database.

## Architecture Overview

```
<backend-src>/
├── domain/              # Pure business rules (entities, value objects, domain services)
├── application/         # Orchestration (use-cases, ports, DTOs)
│   ├── ports/           # Protocol classes for infrastructure
│   └── usecases/        # Business logic orchestration
├── infrastructure/      # Adapters, clients, config, composition
│   ├── adapters/
│   │   ├── driven/      # Outbound (DB, cache, external APIs, queues)
│   │   └── driving/     # Inbound (Litestar controllers, CLI, workers, webhooks)
│   ├── composition/     # DI container
│   └── config/          # Environment configuration
├── shared/              # Cross-cutting types, schemas, helpers
└── scripts/             # Entry points (minimal: parse input, call use-case, format output)
```

### Layer Dependency Rules

```
domain       → imports nothing external (pure)
application  → imports domain only
infrastructure → imports all layers
scripts      → imports via packages, calls use-cases
```

**Enforcement:** Use [import-linter](https://github.com/seddonym/import-linter) to enforce these rules automatically in CI.

---

## 1. Domain Layer (`domain/`)

Pure business rules. **Zero external dependencies** — no SDK, ORM, HTTP, filesystem.

One folder per business subject (aggregate, bounded context):

```
domain/
├── order/
│   ├── order.py              # Entity with business logic
│   ├── test_order.py         # Colocated unit test
│   ├── order_factory.py      # Creation logic
│   └── order_errors.py       # Domain-specific errors
└── shared/                   # Cross-aggregate value objects & rules
```

### Entity Pattern

Entities are immutable with `create` (validates), `rehydrate` (from DB), `to_snapshot` (to DB):

```python
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class OrderSnapshot:
    id: str
    items: list[str]
    status: str

class Order:
    def __init__(self, props: OrderSnapshot) -> None:
        self._props = props

    @staticmethod
    def create(*, id: str, items: list[str]) -> Order:
        if not id:
            raise OrderMissingIdError()
        if not items:
            raise OrderEmptyItemsError()
        return Order(OrderSnapshot(id=id, items=items, status="pending"))

    @staticmethod
    def rehydrate(snapshot: OrderSnapshot) -> Order:
        return Order(snapshot)

    def with_status(self, next_status: str) -> Order:
        allowed = STATUS_TRANSITIONS.get(self._props.status, [])
        if next_status not in allowed:
            raise OrderStatusTransitionError(self._props.status, next_status)
        return Order(OrderSnapshot(
            id=self._props.id,
            items=self._props.items,
            status=next_status,
        ))

    def to_snapshot(self) -> OrderSnapshot:
        return self._props

    @property
    def id(self) -> str:
        return self._props.id

    @property
    def status(self) -> str:
        return self._props.status
```

### Value Objects

Use `dataclass(frozen=True)` for simple values, classes only when validation/behavior is needed:

```python
@dataclass(frozen=True)
class Money:
    amount: float
    currency: str

class OrderId:
    def __init__(self, value: str) -> None:
        if not value or len(value) < 8:
            raise InvalidOrderIdError(value)
        self.value = value
```

### Domain Errors

Typed, catchable, carry context. Define a base `DomainError` with abstract `code`, extend per module:

```python
from abc import abstractmethod

class DomainError(Exception):
    @property
    @abstractmethod
    def code(self) -> str: ...

class OrderStatusTransitionError(DomainError):
    code = "ORDER_INVALID_TRANSITION"

    def __init__(self, from_status: str, to_status: str) -> None:
        super().__init__(f"Cannot transition from '{from_status}' to '{to_status}'")
```

### Domain Services (Pure Functions Only)

Logic that doesn't belong to a single entity. Must be **pure** — no dependencies, no I/O, no async.

```python
def calculate_order_discount(
    items: list[OrderItem],
    customer_tier: CustomerTier,
) -> DiscountResult:
    """Pure computation — no I/O."""
    ...
```

**Rule: If it's `async` or has injected dependencies → it's a use-case, not a domain service.**

---

## 2. Application Layer (`application/`)

Contains **ports** (contracts) and **use-cases** (orchestration). No technology.

### 2.1 Ports (`application/ports/`)

Protocol classes named by **role**, never by technology:

```
application/ports/
├── write/          # Write repositories
├── read/           # Read-optimized queries (light CQRS)
├── messaging/      # Bus, queue, events
├── external/       # Third-party API gateways
├── system/         # Clock, random, config, logging
├── files/          # Storage (local/cloud)
└── compute/        # Generic computation engines
```

```python
from typing import Protocol

class OrderRepositoryPort(Protocol):
    async def save(self, order: OrderSnapshot) -> None: ...
    async def find_by_id(self, id: str) -> OrderSnapshot | None: ...

class PaymentGatewayPort(Protocol):
    async def charge(self, input: ChargeInput) -> ChargeResult: ...
    async def refund(self, transaction_id: str) -> RefundResult: ...
```

### 2.2 Use-Cases (`application/usecases/`)

One folder per use-case. Class with an `execute` method:

```
application/usecases/
├── process_order/
│   ├── process_order_usecase.py
│   └── test_process_order.py
└── cancel_order/
    ├── cancel_order_usecase.py
    └── test_cancel_order.py
```

```python
from dataclasses import dataclass

@dataclass
class ProcessOrderDeps:
    order_repository: OrderRepositoryPort
    payment_gateway: PaymentGatewayPort
    event_bus: EventBusPort
    clock: ClockPort

@dataclass(frozen=True)
class ProcessOrderInput:
    order_id: str
    items: list[str]

@dataclass(frozen=True)
class ProcessOrderResult:
    order_id: str
    status: str

class ProcessOrderUseCase:
    def __init__(self, deps: ProcessOrderDeps) -> None:
        self._deps = deps

    async def execute(self, input: ProcessOrderInput) -> ProcessOrderResult:
        order = Order.create(id=input.order_id, items=input.items)
        await self._deps.payment_gateway.charge(
            ChargeInput(amount=order.total_amount, currency=order.currency)
        )
        confirmed = order.with_status("confirmed")
        await self._deps.order_repository.save(confirmed.to_snapshot())
        await self._deps.event_bus.publish(
            Event(type="ORDER_CONFIRMED", payload={"order_id": confirmed.id})
        )
        return ProcessOrderResult(order_id=confirmed.id, status="confirmed")
```

### 2.3 Steps Pattern (for large use-cases)

Target: **≤ 250–300 lines**. Decompose into `steps/` folder (never `services/`):

```python
class ProcessComplexWorkflowUseCase:
    def __init__(self, deps: Deps) -> None:
        self._deps = deps

    async def execute(self, input: Input) -> Result:
        ctx = WorkflowContext.start(input.data)
        await validate_input_step(self._deps, ctx)
        await build_context_step(self._deps, ctx)
        await run_computation_step(self._deps, ctx)
        await persist_results_step(self._deps, ctx)
        return Result(status="ok", result=ctx.snapshot())
```

### 2.4 Shared Code (`shared/`)

```
shared/
├── types/           # Common DTOs, snapshots, shared enums
├── schemas/         # Pydantic models for validation
└── helpers/         # Reusable utilities (dates, formatters)
```

---

## 3. Infrastructure Layer (`infrastructure/`)

All external concerns: adapters, clients, configuration, composition.

### 3.1 Driven Adapters (Outbound)

Implement ports. One adapter = translation between technology and domain. No business logic.

```python
class SqlOrderRepository:
    def __init__(self, db: AsyncSession, logger: LoggerPort) -> None:
        self._db = db
        self._logger = logger

    async def save(self, snapshot: OrderSnapshot) -> None:
        stmt = insert(OrderTable).values(
            id=snapshot.id, status=snapshot.status
        ).on_conflict_do_update(index_elements=["id"], set_={"status": snapshot.status})
        await self._db.execute(stmt)
        await self._db.commit()

    async def find_by_id(self, id: str) -> OrderSnapshot | None:
        result = await self._db.execute(
            select(OrderTable).where(OrderTable.id == id)
        )
        row = result.scalar_one_or_none()
        return self._to_domain(row) if row else None

    def _to_domain(self, row: OrderTable) -> OrderSnapshot:
        return OrderSnapshot(id=row.id, items=row.items, status=row.status)
```

### 3.2 Driving Adapters (Inbound) — Litestar Controllers

Parse input, validate, call use-case, format output. **No business logic.** Auth lives in guards/middleware — use-cases receive an already-authenticated context.

```python
from litestar import Controller, post, get
from litestar.di import Provide

class OrderController(Controller):
    path = "/orders"

    @post("/")
    async def create_order(
        self,
        data: CreateOrderRequest,
        process_order: ProcessOrderUseCase,
    ) -> OrderResponse:
        result = await process_order.execute(
            ProcessOrderInput(order_id=data.order_id, items=data.items)
        )
        return OrderResponse(order_id=result.order_id, status=result.status)
```

### 3.3 Error Propagation (Domain → HTTP)

Centralized exception handler maps `DomainError.code` to HTTP status. Use-cases throw `DomainError` subclasses — never construct HTTP responses.

```python
from litestar import Request, Response
from litestar.exceptions import HTTPException

DOMAIN_ERROR_STATUS_MAP: dict[str, int] = {
    "ORDER_MISSING_ID": 400,
    "ORDER_INVALID_TRANSITION": 409,
    "ORDER_NOT_FOUND": 404,
    "INSUFFICIENT_CREDITS": 402,
}

def domain_error_handler(request: Request, exc: DomainError) -> Response:
    status = DOMAIN_ERROR_STATUS_MAP.get(exc.code, 500)
    return Response(
        content={"error": exc.code, "message": str(exc)},
        status_code=status,
    )

# Register in Litestar app:
# app = Litestar(exception_handlers={DomainError: domain_error_handler})
```

### 3.4 Composition Root (`infrastructure/composition/`)

**Separate factory functions** for production and test. No DI framework.

```python
# PRODUCTION — infrastructure/composition/container.py
from dataclasses import dataclass

@dataclass
class AppContainer:
    process_order: ProcessOrderUseCase
    cancel_order: CancelOrderUseCase

def create_app_container(settings: Settings) -> AppContainer:
    db = create_async_session(settings.database_url)
    logger = StructlogAdapter()
    order_repo = SqlOrderRepository(db, logger)
    payment = PaymentProviderGateway(settings.payment_api_key, logger)
    event_bus = RedisEventBus(settings.redis_url, logger)
    clock = SystemClock()

    return AppContainer(
        process_order=ProcessOrderUseCase(ProcessOrderDeps(
            order_repository=order_repo,
            payment_gateway=payment,
            event_bus=event_bus,
            clock=clock,
        )),
        cancel_order=CancelOrderUseCase(...),
    )
```

```python
# TEST — tests/utils/test_container.py
def create_test_container(
    *,
    order_repository: OrderRepositoryPort | None = None,
    payment_gateway: PaymentGatewayPort | None = None,
    event_bus: EventBusPort | None = None,
    clock: ClockPort | None = None,
) -> AppContainer:
    repo = order_repository or InMemoryOrderRepository()
    payment = payment_gateway or StubPaymentGateway()
    bus = event_bus or InMemoryEventBus()
    clk = clock or FixedClock("2024-01-01T00:00:00Z")

    return AppContainer(
        process_order=ProcessOrderUseCase(ProcessOrderDeps(
            order_repository=repo,
            payment_gateway=payment,
            event_bus=bus,
            clock=clk,
        )),
        cancel_order=CancelOrderUseCase(...),
    )
```

### 3.5 Litestar App Wiring

```python
from litestar import Litestar

def create_app(container: AppContainer | None = None) -> Litestar:
    if container is None:
        settings = Settings()
        container = create_app_container(settings)

    return Litestar(
        route_handlers=[OrderController],
        dependencies={
            "process_order": Provide(lambda: container.process_order),
            "cancel_order": Provide(lambda: container.cancel_order),
        },
        exception_handlers={DomainError: domain_error_handler},
    )
```

### 3.6 Configuration

One file reads environment: `infrastructure/config/settings.py`. **Zero** `os.environ` access anywhere else.

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str = "redis://localhost:6379"
    payment_api_key: str

    model_config = {"env_file": ".env"}
```

### 3.7 Structured Logging

Inject `LoggerPort` — never call `print()` directly. Use [structlog](https://www.structlog.org/) for structured output. Log at boundaries: use-case entry/exit, external adapter calls, recoverable failures (warn), unrecoverable failures (error + traceback).

---

## 4. Naming Conventions

| Type | Suffix | Example |
|------|--------|---------|
| Entity | none | `order.py` |
| Value Object | none | `money.py` |
| Domain Error | `_errors` | `order_errors.py` |
| Port | `_port` | `order_repository_port.py` |
| Use-case | `_usecase` | `process_order_usecase.py` |
| Step | `_step` | `validate_input_step.py` |
| Adapter | class name | `sql_order_repository.py` |
| Controller | `_controller` | `order_controller.py` |
| Test | `test_` prefix | `test_order.py` |

When a folder exceeds **5–6 files**, group by scope.

---

## 5. `__init__.py` Policy

**Required:** Module entry points, layer entry points, folders with 2+ public symbols to group.

**Forbidden:** Folders with 1 file, individual use-case folders, cascading re-exports across layers.

---

## 6. Testing Strategy

> Examples use **pytest** + **pytest-asyncio**.

### 6.1 Test Types

| Type | Scope | Mocking |
|------|-------|---------|
| **Domain unit** | Entities, value objects, pure services | None |
| **Use-case integration** | Use-cases with fake ports | In-memory adapters, fixed clock |
| **Adapter/infra** | Repositories, gateways | Real adapter, controlled backend |
| **HTTP integration** | Full stack via Litestar test client | In-memory adapters, real use-cases |

### 6.2 What to Mock

**Always mock ports** with in-memory adapters:

```python
clock = FixedClock("2024-01-01T00:00:00Z")
repository = InMemoryOrderRepository()
```

**Never mock:** entities, use-cases in HTTP tests, the DI container.

**Forbidden:** `MagicMock()` on port methods (use in-memory adapters instead), `cast(Any, ...)` hacks on entities, mocks that re-implement business logic.

### 6.3 Test Rules

- **AAA pattern** (Arrange — Act — Assert)
- Test **observable behavior**, never internal implementation
- Never inspect private fields via `_props`
- Never duplicate test data — use shared factories
- Colocate unit tests next to source (`test_order.py` beside `order.py`)

### 6.4 HTTP Tests with Litestar

```python
import pytest
from litestar.testing import AsyncTestClient

@pytest.fixture
def test_container() -> AppContainer:
    return create_test_container()

@pytest.fixture
async def client(test_container: AppContainer):
    app = create_app(container=test_container)
    async with AsyncTestClient(app) as client:
        yield client

async def test_create_order_returns_200(client: AsyncTestClient, test_container: AppContainer):
    # Arrange — seed data
    test_container.process_order._deps.order_repository.seed([...])

    # Act
    response = await client.post("/orders", json={"order_id": "abc", "items": ["x"]})

    # Assert
    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"
```

---

## 7. Forbidden Patterns

1. **No `services/` folder** at backend root — use `application/usecases/`
2. **No `services/` inside a use-case** — use `steps/`, `helpers/`, `mappers/`
3. **No inline static content** > 20 lines in use-cases
4. **No `os.environ`** outside `infrastructure/config/`
5. **No useless `__init__.py`** that only re-export one thing
6. **No async domain services** — async = use-case
7. **No collapsing layers** "because it's simple"
8. **No `MagicMock()`** on port methods — write in-memory adapters
9. **No silent error swallowing** — every `except` must reraise, log+reraise, or return typed error
10. **No business logic in controllers** — controllers are thin wrappers

---

## 8. Delivery Checklist

1. Define business rules → `domain/`
2. Define domain errors → `domain/<module>/_errors.py`
3. Define/extend ports → `application/ports/`
4. Code use-cases + tests → `application/usecases/`
5. Implement adapters + integration tests → `infrastructure/adapters/`
6. Add error handler → `infrastructure/adapters/driving/http/`
7. Wire the container → `infrastructure/composition/`
8. Expose via Litestar controller/CLI/worker → `infrastructure/adapters/driving/`
9. Run ruff, mypy, pytest
10. Run import-linter dependency check

---

## 9. Placement Cheat Sheet

| Logic | Location |
|-------|----------|
| Business rules, entities, errors | `domain/<module>/` |
| Value objects, pure domain services | `domain/<module>/` or `domain/shared/` |
| Orchestration (use-cases) | `application/usecases/<case>/` |
| Use-case steps | `application/usecases/<case>/steps/` |
| Port protocols | `application/ports/<category>/` |
| Shared types/schemas/helpers | `shared/` |
| DB/cache/external adapters | `infrastructure/adapters/driven/` |
| Litestar controllers/CLI/workers | `infrastructure/adapters/driving/` |
| DI composition | `infrastructure/composition/` (prod) / `tests/utils/` (test) |
| Environment config | `infrastructure/config/` |
| Static content (prompts, templates) | `application/templates/` or adapter-specific |

---

## 10. End-to-End Example: "Transfer Credits"

**Business rule:** A user transfers credits to another user. Sender must have enough. Both balances update atomically.

**Domain** — immutable `Wallet` entity:

```python
@dataclass(frozen=True)
class WalletSnapshot:
    user_id: str
    balance: float

class Wallet:
    def __init__(self, props: WalletSnapshot) -> None:
        self._props = props

    @staticmethod
    def create(user_id: str, balance: float) -> Wallet:
        if balance < 0:
            raise NegativeBalanceError(user_id)
        return Wallet(WalletSnapshot(user_id=user_id, balance=balance))

    @staticmethod
    def rehydrate(snapshot: WalletSnapshot) -> Wallet:
        return Wallet(snapshot)

    def debit(self, amount: float) -> Wallet:
        if self._props.balance < amount:
            raise InsufficientCreditsError(self._props.user_id, amount)
        return Wallet(WalletSnapshot(
            user_id=self._props.user_id,
            balance=self._props.balance - amount,
        ))

    def credit(self, amount: float) -> Wallet:
        return Wallet(WalletSnapshot(
            user_id=self._props.user_id,
            balance=self._props.balance + amount,
        ))

    def to_snapshot(self) -> WalletSnapshot:
        return self._props

    @property
    def balance(self) -> float:
        return self._props.balance
```

**Port:**

```python
class WalletRepositoryPort(Protocol):
    async def find_by_user_id(self, user_id: str) -> WalletSnapshot | None: ...
    async def save_all(self, wallets: list[WalletSnapshot]) -> None:
        """Must run in a single transaction."""
        ...
```

**Use-Case:**

```python
@dataclass(frozen=True)
class TransferCreditsInput:
    sender_id: str
    receiver_id: str
    amount: float

@dataclass(frozen=True)
class TransferCreditsResult:
    sender_balance: float
    receiver_balance: float

class TransferCreditsUseCase:
    def __init__(self, deps: TransferCreditsDeps) -> None:
        self._deps = deps

    async def execute(self, input: TransferCreditsInput) -> TransferCreditsResult:
        sender_snap, receiver_snap = await asyncio.gather(
            self._deps.wallet_repository.find_by_user_id(input.sender_id),
            self._deps.wallet_repository.find_by_user_id(input.receiver_id),
        )
        if not sender_snap:
            raise WalletNotFoundError(input.sender_id)
        if not receiver_snap:
            raise WalletNotFoundError(input.receiver_id)

        sender = Wallet.rehydrate(sender_snap).debit(input.amount)
        receiver = Wallet.rehydrate(receiver_snap).credit(input.amount)

        await self._deps.wallet_repository.save_all([
            sender.to_snapshot(), receiver.to_snapshot()
        ])
        return TransferCreditsResult(
            sender_balance=sender.balance,
            receiver_balance=receiver.balance,
        )
```

**Use-Case Test:**

```python
async def test_transfers_credits_between_users():
    repo = InMemoryWalletRepository()
    repo.seed([
        WalletSnapshot(user_id="alice", balance=100),
        WalletSnapshot(user_id="bob", balance=20),
    ])
    usecase = TransferCreditsUseCase(TransferCreditsDeps(wallet_repository=repo))

    result = await usecase.execute(TransferCreditsInput(
        sender_id="alice", receiver_id="bob", amount=30,
    ))

    assert result == TransferCreditsResult(sender_balance=70, receiver_balance=50)
```

**HTTP Test:**

```python
async def test_transfer_returns_200(client: AsyncTestClient, test_container: AppContainer):
    test_container.transfer_credits._deps.wallet_repository.seed([
        WalletSnapshot(user_id="alice", balance=100),
        WalletSnapshot(user_id="bob", balance=20),
    ])

    response = await client.post(
        "/transfers",
        json={"receiver_id": "bob", "amount": 30},
        headers={"Authorization": "Bearer alice-token"},
    )

    assert response.status_code == 200
    assert response.json() == {"sender_balance": 70, "receiver_balance": 50}
```

---

## Tooling Stack

| Concern | Tool |
|---------|------|
| Framework | [Litestar](https://litestar.dev/) |
| Linting + Formatting | [ruff](https://docs.astral.sh/ruff/) |
| Type checking | [mypy](https://mypy-lang.org/) (strict) or [pyright](https://github.com/microsoft/pyright) |
| Testing | [pytest](https://docs.pytest.org/) + [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio) |
| Validation/Settings | [Pydantic](https://docs.pydantic.dev/) + [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) |
| Structured logging | [structlog](https://www.structlog.org/) |
| Layer enforcement | [import-linter](https://github.com/seddonym/import-linter) |
| ORM (optional) | [SQLAlchemy 2.0](https://docs.sqlalchemy.org/) async |

## Resources

- **Clean Architecture** (Robert C. Martin)
- **Hexagonal Architecture** (Alistair Cockburn)
- **Domain-Driven Design** (Eric Evans)
- **Implementing Domain-Driven Design** (Vaughn Vernon)
- [import-linter](https://github.com/seddonym/import-linter)
- [Litestar documentation](https://docs.litestar.dev/)
