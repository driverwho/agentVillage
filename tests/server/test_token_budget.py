from server.llm.token_budget import TokenBudget, BudgetStatus

def test_token_budget_exhaustion():
    budget = TokenBudget(daily_limit=100)
    assert budget.status == BudgetStatus.NORMAL
    budget.consume(80)
    assert budget.status == BudgetStatus.WARNING
    budget.consume(20)
    assert budget.status == BudgetStatus.EXHAUSTED
    assert budget.consume(1) == False

def test_token_budget_reset():
    budget = TokenBudget(daily_limit=100)
    budget.consume(50)
    budget.reset()
    assert budget.used == 0
    assert budget.status == BudgetStatus.NORMAL
