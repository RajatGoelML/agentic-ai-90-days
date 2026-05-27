"""
DEBUG SCRIPT: Step-by-step execution of Reversal Intelligence Engine
Run this to see detailed execution flow with inspection points
"""

import sys
from pathlib import Path

# Add workspace to path
workspace_root = Path(__file__).parent
sys.path.insert(0, str(workspace_root))

from reversal_intelligence_engine.engine.scheduler import get_next_nodes
from reversal_intelligence_engine.engine.utils.state_updater import apply_node_result
from reversal_intelligence_engine.reversal_strategy.registry.node_registry import NODE_REGISTRY
from reversal_intelligence_engine.reversal_strategy.graph.graph_config import GRAPH
from reversal_intelligence_engine.engine.executor import execute_nodes_in_parallel
from reversal_intelligence_engine.engine.state.state_model import initialize_state
from reversal_intelligence_engine.reversal_strategy.agents.llm_client import token_tracker


class Debugger:
    """Enhanced debugger with step-by-step execution"""
    
    def __init__(self):
        self.iteration = 0
        self.execution_log = []
    
    def print_separator(self, title=""):
        print("\n" + "="*80)
        if title:
            print(f"  {title}")
            print("="*80)
    
    def print_state_snapshot(self, state, label="State"):
        """Print current state in readable format"""
        self.print_separator(f"{label} SNAPSHOT (Iteration {self.iteration})")
        print(f"📊 Completed Nodes: {state['completed_nodes']}")
        print(f"📊 Node Results: {list(state.get('node_results', {}).keys())}")
        if 'watchlist' in state:
            print(f"📊 Watchlist Items: {len(state.get('watchlist', []))}")
    
    def print_graph_info(self):
        """Print workflow graph structure"""
        self.print_separator("WORKFLOW GRAPH STRUCTURE")
        for node, dependencies in GRAPH.items():
            deps_str = f"depends on {dependencies}" if dependencies else "ROOT NODE"
            print(f"  • {node}: {deps_str}")
    
    def print_next_nodes(self, next_nodes):
        """Print next nodes to execute"""
        self.print_separator(f"EXECUTION PLAN (Step {self.iteration})")
        if next_nodes:
            print(f"🎯 Next Nodes to Run: {next_nodes}")
        else:
            print("🎯 All nodes completed!")
    
    def print_execution_result(self, results):
        """Print results of execution"""
        self.print_separator(f"EXECUTION RESULTS (Step {self.iteration})")
        for item in results:
            node_name = item["node"]
            success = item["success"]
            status = "✅ SUCCESS" if success else "❌ FAILED"
            print(f"\n  {node_name}: {status}")
            
            if success:
                result = item["result"]
                if hasattr(result, 'data'):
                    print(f"    Data Keys: {list(result.data.keys())}")
                    for key, value in result.data.items():
                        if isinstance(value, (list, dict)):
                            print(f"      • {key}: {type(value).__name__} (len={len(value)})")
                        else:
                            print(f"      • {key}: {str(value)[:60]}")
            else:
                print(f"    Error: {item.get('error', 'Unknown')}")
    
    def run_debug_workflow(self, max_iterations=None):
        """Execute workflow with debug output"""
        token_tracker.reset()
        state = initialize_state()
        
        self.print_separator("🚀 REVERSAL INTELLIGENCE ENGINE - DEBUG MODE")
        self.print_graph_info()
        self.print_state_snapshot(state, "INITIAL STATE")
        
        iteration_count = 0
        max_iterations = max_iterations or 100
        
        while iteration_count < max_iterations:
            self.iteration = iteration_count + 1
            iteration_count += 1
            
            print("\n" + "▶️ " * 30)
            
            # Get next nodes
            next_nodes = get_next_nodes(GRAPH, state["completed_nodes"])
            self.print_next_nodes(next_nodes)
            
            if not next_nodes:
                print("\n✨ Workflow completed!")
                break
            
            # Execute nodes
            print(f"\n⏳ Executing nodes in parallel...")
            results = execute_nodes_in_parallel(next_nodes, NODE_REGISTRY, state)
            
            # Print results
            self.print_execution_result(results)
            
            # Apply results
            print("\n🔄 Applying results to state...")
            for item in results:
                node_name = item["node"]
                if item["success"]:
                    result = item["result"]
                    apply_node_result(state, result)
                    print(f"   ✓ {node_name} state updated")
                state["completed_nodes"].add(node_name)
            
            # Print state after iteration
            self.print_state_snapshot(state, "STATE AFTER ITERATION")
        
        # Final summary
        self.print_separator("📋 FINAL SUMMARY")
        print(f"✅ Total Iterations: {iteration_count}")
        print(f"✅ Completed Nodes: {state['completed_nodes']}")
        print(f"✅ Token Usage: {token_tracker.get_summary()}")
        
        token_tracker.print_summary()
        
        return state


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Debug Reversal Intelligence Engine")
    parser.add_argument("--max-iterations", type=int, default=None, help="Max iterations to run")
    parser.add_argument("--step-mode", action="store_true", help="Pause after each step")
    
    args = parser.parse_args()
    
    debugger = Debugger()
    
    if args.step_mode:
        print("📌 STEP MODE ENABLED - Press Enter to continue after each iteration...")
        original_method = debugger.print_separator
        def step_pause(*args, **kwargs):
            original_method(*args, **kwargs)
            input("Press Enter to continue... ")
        debugger.print_separator = step_pause
    
    output = debugger.run_debug_workflow(max_iterations=args.max_iterations)
