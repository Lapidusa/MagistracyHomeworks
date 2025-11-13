#%%
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import ast
import operator as op

app = FastAPI(
  title="Async Calculator",
  description="Домашка по FastAPI: простой калькулятор с выражениями",
)

class BinaryOpRequest(BaseModel):
  a: float
  b: float

class ExpressionRequest(BaseModel):
  expression: str

class ExpressionState(BaseModel):
  expression: Optional[str]
  last_result: Optional[float]


current_expression: Optional[str] = None
last_result: Optional[float] = None


@app.post("/add")
async def add(data: BinaryOpRequest):
  return {"result": data.a + data.b}


@app.post("/sub")
async def sub(data: BinaryOpRequest):
  return {"result": data.a - data.b}


@app.post("/mul")
async def mul(data: BinaryOpRequest):
  return {"result": data.a * data.b}


@app.post("/div")
async def div(data: BinaryOpRequest):
  if data.b == 0:
    raise HTTPException(status_code=400, detail="Division by zero")
  return {"result": data.a / data.b}

_ALLOWED_BIN_OPS = {
  ast.Add: op.add,
  ast.Sub: op.sub,
  ast.Mult: op.mul,
  ast.Div: op.truediv,
}

_ALLOWED_UNARY_OPS = {
  ast.UAdd: op.pos,
  ast.USub: op.neg,
}


def _eval_ast(node: ast.AST) -> float:
  if isinstance(node, ast.Expression):
    return _eval_ast(node.body)

  if isinstance(node, ast.Constant):
    if isinstance(node.value, (int, float)):
      return float(node.value)
    raise ValueError("Allowed only numeric constants")

  if isinstance(node, ast.BinOp):
    left = _eval_ast(node.left)
    right = _eval_ast(node.right)
    op_type = type(node.op)
    if op_type not in _ALLOWED_BIN_OPS:
      raise ValueError(f"Operation {op_type.__name__} is not allowed")
    if op_type is ast.Div and right == 0:
      raise ZeroDivisionError("Division by zero in expression")
    return _ALLOWED_BIN_OPS[op_type](left, right)

  if isinstance(node, ast.UnaryOp):
    operand = _eval_ast(node.operand)
    op_type = type(node.op)
    if op_type not in _ALLOWED_UNARY_OPS:
      raise ValueError(f"Operation {op_type.__name__} is not allowed")
    return _ALLOWED_UNARY_OPS[op_type](operand)

  raise ValueError(f"Unsupported expression element: {type(node).__name__}")


def evaluate_expression(expr: str) -> float:
  try:
    tree = ast.parse(expr, mode="eval")
  except SyntaxError:
    raise ValueError("Invalid expression syntax")
  return _eval_ast(tree)


@app.post("/expression", response_model=ExpressionState)
async def set_expression(req: ExpressionRequest):
  global current_expression, last_result
  current_expression = req.expression
  last_result = None
  return ExpressionState(expression=current_expression, last_result=last_result)


@app.get("/expression", response_model=ExpressionState)
async def get_expression():
  return ExpressionState(expression=current_expression, last_result=last_result)


@app.post("/expression/execute")
async def execute_expression(req: ExpressionRequest | None = None):
  global current_expression, last_result

  expr = None
  if req is not None and req.expression:
    expr = req.expression
    current_expression = expr
  else:
    expr = current_expression

  if not expr:
    raise HTTPException(
      status_code=400,
      detail="Expression is not set. Send it in body or call /expression first.",
    )

  try:
    result = evaluate_expression(expr)
  except ZeroDivisionError as e:
    raise HTTPException(status_code=400, detail=str(e))
  except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))

  last_result = result
  return {"expression": expr, "result": result}


if __name__ == "__main__":
  import uvicorn
  uvicorn.run("hw6t7_app:app", host="127.0.0.1", port=8000, reload=True)
