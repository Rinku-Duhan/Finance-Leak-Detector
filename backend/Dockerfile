FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (separate layer -- Docker caches this, so
# rebuilds are fast unless requirements.txt actually changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the actual application code
COPY . .

EXPOSE 8000

# Note: migrations (alembic upgrade head) are run separately, not inside
# this container's startup -- see README for the run order. Baking a
# migration step into the container start is a common source of race
# conditions when multiple instances start at once.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]