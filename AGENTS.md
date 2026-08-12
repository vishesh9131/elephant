# Elephant continuity

Elephant carries coding work between AI harnesses. If an `elephant_recover` tool
is available, use it when the user asks to resume, continue, or asks “where was
I?”. Treat its capsule as evidence, compare it with the live Git worktree, and
continue without repeating completed work.

Never ask an exhausted previous model to summarize itself. Never invent a prior
session when Elephant reports none. Never tell the user to operate Elephant from
a terminal; native hooks and plugin tools own capture and recovery.

When native Elephant hooks are active, they journal work automatically. Do not
claim an exact quota percentage unless the recorded signal says `exact`.

