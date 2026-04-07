# Workflows Directory

Purpose:
--------
Stores persisted workflow state files.

Each file represents a single workflow execution:
    <workflow_id>.json

Characteristics:
----------------
- Created automatically at runtime.
- Updated after every valid FSM transition.
- Enables crash recovery and execution resumption.

This directory is intentionally local (Day 12 phase).
Future phases may centralize storage via configurable backends.