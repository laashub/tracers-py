from sysdig_tracer import Tracer, Args, ReturnValue, Kwds
import sysdig_tracer
import os
import fcntl
import sys
import pytest

# hack to send tracers to a pipe and allow unit testing
read_end, write_end = os.pipe()
sysdig_tracer.NULL_FD = write_end
fcntl.fcntl(read_end, fcntl.F_SETFL, os.O_NONBLOCK)

def check_pipe_content(s):
  content = ""
  try:
    content = os.read(read_end, 1024)
    if sys.version_info[0] == 3:
      content = str(content, 'ascii')
  except:
    pass
  assert content == s

def test_with():
  with Tracer("myname"):
    x = 5
    y = 6
  check_pipe_content(">:t:myname::<:t:myname::")

def test_with_and_args():
  with Tracer("myname", {"x": "8"}):
    x = 5
    y = 6
  check_pipe_content(">:t:myname:x=8:<:t:myname::")

def test_auto_naming():
  with Tracer():
    x = 5
    y = 6
  check_pipe_content(">:t:tracer-py/test\\.py\\:36(test_auto_naming)::<:t:tracer-py/test\\.py\\:36(test_auto_naming)::")

def test_decorator():
  @Tracer
  def myfunction():
    x = 5
    y = 6
  myfunction()
  check_pipe_content(">:t:myfunction::<:t:myfunction::")

def test_start_stop():
  t = Tracer()
  t.start()
  x = 8
  y = 5
  t.stop(args={"x": x})
  check_pipe_content(">:t:tracer-py/test\\.py\\:51(test_start_stop)::<:t:tracer-py/test\\.py\\:51(test_start_stop):x=8:")

  t.start("mytest")
  y = 6
  x = 7
  t.stop(args={"x": x})
  check_pipe_content(">:t:mytest::<:t:mytest:x=7:")

def test_auto_naming_in_nested_scope():
  def f():
    with Tracer():
      x = 5
      y = 6
  def g():
    f()
  g()
  check_pipe_content(">:t:tracer-py/test\\.py\\:65(f)::<:t:tracer-py/test\\.py\\:65(f)::")

def test_nested_tracer():
  with Tracer("g") as g:
    x = 8
    with g.span("f"):
      y = 8
    with g.span("h") as h:
      p = 19
      with h.span("u"):
        u = 80
  check_pipe_content(">:t:g::>:t:g.f::<:t:g.f::>:t:g.h::>:t:g.h.u::<:t:g.h.u::<:t:g.h::<:t:g::")

def test_nested_tracer_autonaming():
  with Tracer() as g:
    x = 8
    with g.span():
      y = 8
    with g.span() as h:
      p = 19
      with h.span():
        u = 80

  check_pipe_content(
    ">:t:tracer-py/test\.py\:85(test_nested_tracer_autonaming)::"
    ">:t:tracer-py/test\.py\:85(test_nested_tracer_autonaming).tracer-py/test\.py\:87(test_nested_tracer_autonaming)::"
    "<:t:tracer-py/test\.py\:85(test_nested_tracer_autonaming).tracer-py/test\.py\:87(test_nested_tracer_autonaming)::"
    ">:t:tracer-py/test\.py\:85(test_nested_tracer_autonaming).tracer-py/test\.py\:89(test_nested_tracer_autonaming)::"
    ">:t:tracer-py/test\.py\:85(test_nested_tracer_autonaming).tracer-py/test\.py\:89(test_nested_tracer_autonaming).tracer-py/test\.py\:91(test_nested_tracer_autonaming)::"
    "<:t:tracer-py/test\.py\:85(test_nested_tracer_autonaming).tracer-py/test\.py\:89(test_nested_tracer_autonaming).tracer-py/test\.py\:91(test_nested_tracer_autonaming)::"
    "<:t:tracer-py/test\.py\:85(test_nested_tracer_autonaming).tracer-py/test\.py\:89(test_nested_tracer_autonaming)::"
    "<:t:tracer-py/test\.py\:85(test_nested_tracer_autonaming)::"
    )

def test_decorator_complex():
  @Tracer
  def myfunction(x, y):
    return x*y
  assert myfunction(3, 4) == 12
  check_pipe_content(">:t:myfunction::<:t:myfunction::")

def test_decorator_complex_args():
  @Tracer(enter_args={"iterative": 1})
  def myfunction(x, y):
    return x*y
  assert myfunction(3, 4) == 12
  check_pipe_content(">:t:myfunction::<:t:myfunction::")

def test_exit_args():
  @Tracer(enter_args={"n": Args(0)}, exit_args={"ret": ReturnValue})
  def factorial(n):
    ret = 1
    while n > 0:
      ret *= n
      n -= 1
    return ret
  assert factorial(9) == 9*8*7*6*5*4*3*2*1
  check_pipe_content(">:t:factorial:n=9:<:t:factorial:ret=362880:")

def test_exit_kwds():
  @Tracer(enter_args={"n": Kwds("n")}, exit_args={"ret": ReturnValue})
  def factorial(n):
    ret = 1
    while n > 0:
      ret *= n
      n -= 1
    return ret
  assert factorial(n=9) == 9*8*7*6*5*4*3*2*1
  check_pipe_content(">:t:factorial:n=9:<:t:factorial:ret=362880:")

def test_decorator_as_method():
  class MyTestClass(object):
    def __init__(self):
      self.x = 90

    @Tracer
    def doWork(self):
      y = self.x + 80

  inst = MyTestClass()
  inst.doWork()
  check_pipe_content(">:t:doWork::<:t:doWork::")