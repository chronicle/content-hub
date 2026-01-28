# Golden Standard Examples

> **Instructions:**
> Provide 3-5 examples of "Perfect" interactions. This is the strongest signal you can give the
> Judge LLM.

## Example 1

**User Input:** "How many users signed up last week?"
**Ideal Output:**

```sql
SELECT count(*)
FROM `project.dataset.users`
WHERE signup_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
```

## Example 2

**User Input:** "Show me the top 5 products by revenue."
**Ideal Output:**

```sql
SELECT product_name, sum(revenue) as total_rev
FROM `project.dataset.sales`
GROUP BY 1
ORDER BY 2 DESC LIMIT 5
```