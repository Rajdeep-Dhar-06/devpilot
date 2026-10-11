# Seed Issues for DevPilot Evaluation (Decision 15)

### Issue #1 (Feature - Easy)
**Title:** Add `power(base, exponent)` function
**Description:**
The calculator is missing an exponentiation function. Implement `power(base: float, exponent: float) -> float` in `calculator/calc.py`, export it in `calculator/__init__.py`, and add unit tests verifying positive and negative exponents.

---

### Issue #2 (Bugfix - Medium)
**Title:** Handle negative exponents gracefully with bounds check
**Description:**
When evaluating `power(0.0, -1.0)`, ensure a `ValueError` or `ZeroDivisionError` is raised with a descriptive message rather than producing an unhandled exception or math domain error. Add comprehensive edge-case tests.

---

### Issue #3 (Security & Edge Cases - Hard)
**Title:** Protect against resource exhaustion via excessive exponent values
**Description:**
Calculating `power(10.0, 1000000000.0)` causes `OverflowError` or CPU exhaustion. Add maximum magnitude input validation for exponents (`abs(exponent) <= 10000`), raising `ValueError("Exponent exceeds maximum allowed magnitude")`.
