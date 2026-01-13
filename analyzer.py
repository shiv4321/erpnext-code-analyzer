"""
ERPNext Code Analyzer - Terminal Version
=========================================
Simple MVP that analyzes Python code structure and relationships.
Pure terminal output - no web server needed!

Usage:
    python analyzer.py
"""

import ast
import json
from pathlib import Path
from collections import defaultdict
import sys

# ============================================================================
# PART 1: CODE EXTRACTION - Finding classes, functions, and imports
# ============================================================================

def extract_entities(file_path):
    """
    Extract all classes, functions, and imports from a Python file.
    
    How it works:
    1. Read the file content
    2. Parse it into an AST (Abstract Syntax Tree)
    3. Walk through the tree to find classes, functions, and imports
    
    Returns: dict with 'classes', 'functions', 'imports'
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
        
        # Parse the Python code into an AST
        # Think of AST as a structured representation of code
        tree = ast.parse(source_code, filename=str(file_path))
        
        entities = {
            'classes': [],
            'functions': [],
            'imports': []
        }
        
        # Walk through every node in the tree
        for node in ast.walk(tree):
            # Found a class definition?
            if isinstance(node, ast.ClassDef):
                entities['classes'].append({
                    'name': node.name,
                    'line': node.lineno,
                    'methods': [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                })
            
            # Found a function definition (not inside a class)?
            elif isinstance(node, ast.FunctionDef):
                entities['functions'].append({
                    'name': node.name,
                    'line': node.lineno,
                    'args': [arg.arg for arg in node.args.args]
                })
            
            # Found an import statement?
            elif isinstance(node, ast.Import):
                for name in node.names:
                    entities['imports'].append(name.name)
            
            # Found a "from X import Y" statement?
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    entities['imports'].append(node.module)
        
        return entities
    
    except Exception as e:
        return None


def find_function_calls(file_path):
    """
    Find all function calls in a file.
    This helps us understand "what calls what" (relationships).
    
    Returns: list of tuples (caller_context, called_function)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
        
        tree = ast.parse(source_code, filename=str(file_path))
        calls = []
        
        # We need to track which function we're currently inside
        # This is called "scope tracking"
        class CallVisitor(ast.NodeVisitor):
            def __init__(self):
                self.current_scope = "module_level"
            
            def visit_FunctionDef(self, node):
                # When we enter a function, remember its name
                old_scope = self.current_scope
                self.current_scope = node.name
                self.generic_visit(node)  # Visit children
                self.current_scope = old_scope  # Restore old scope
            
            def visit_Call(self, node):
                # Found a function call!
                called_name = None
                
                # Extract the name of what's being called
                if isinstance(node.func, ast.Name):
                    called_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    called_name = node.func.attr
                
                if called_name:
                    calls.append((self.current_scope, called_name))
                
                self.generic_visit(node)
        
        visitor = CallVisitor()
        visitor.visit(tree)
        
        return calls
    
    except Exception as e:
        return []


def analyze_directory(directory_path, max_files=100):
    """
    Analyze all Python files in a directory.
    
    Args:
        directory_path: Path to analyze
        max_files: Limit to prevent analyzing huge codebases (MVP!)
    
    Returns: dict with all analysis results
    """
    path = Path(directory_path)
    
    if not path.exists():
        print(f"\n❌ ERROR: Directory not found: {directory_path}")
        print("\n💡 Tips:")
        print("   - Check if the path is correct")
        print("   - Use forward slashes: C:/Users/...")
        print("   - Or double backslashes: C:\\\\Users\\\\...")
        return None
    
    # Find all Python files
    python_files = list(path.rglob('*.py'))[:max_files]
    
    if len(python_files) == 0:
        print(f"\n⚠️  No Python files found in: {directory_path}")
        return None
    
    all_entities = []
    all_calls = []
    file_count = 0
    
    print(f"\n🔍 Found {len(python_files)} Python files. Analyzing...")
    print("─" * 60)
    
    for py_file in python_files:
        # Extract entities (classes, functions, imports)
        entities = extract_entities(py_file)
        if entities:
            entities['file'] = str(py_file.relative_to(path))
            all_entities.append(entities)
            file_count += 1
        
        # Extract function calls (relationships)
        calls = find_function_calls(py_file)
        all_calls.extend(calls)
        
        # Show progress
        if file_count % 10 == 0:
            print(f"  ✓ Processed {file_count} files...")
    
    print(f"  ✓ Completed! Analyzed {file_count} files.")
    print("─" * 60)
    
    # Count statistics
    total_classes = sum(len(e['classes']) for e in all_entities)
    total_functions = sum(len(e['functions']) for e in all_entities)
    total_imports = sum(len(e['imports']) for e in all_entities)
    
    # Find most called functions
    call_counts = defaultdict(int)
    for _, called in all_calls:
        call_counts[called] += 1
    
    most_called = sorted(call_counts.items(), key=lambda x: x[1], reverse=True)[:15]
    
    # Find functions that call the most others (orchestrators)
    caller_counts = defaultdict(set)
    for caller, called in all_calls:
        if caller != "module_level":
            caller_counts[caller].add(called)
    
    orchestrators = sorted(
        [(caller, len(callees)) for caller, callees in caller_counts.items()],
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    return {
        'summary': {
            'files_analyzed': file_count,
            'total_classes': total_classes,
            'total_functions': total_functions,
            'total_imports': total_imports,
            'total_calls': len(all_calls),
            'most_called': most_called,
            'orchestrators': orchestrators
        },
        'entities': all_entities,
        'calls': all_calls[:1000]  # Limit for performance
    }


# ============================================================================
# PART 2: TERMINAL OUTPUT - Beautiful formatting for console
# ============================================================================

def print_banner():
    """Print a nice banner"""
    print("\n")
    print("═" * 70)
    print("  🔍 ERPNext Code Analyzer - Terminal Edition")
    print("═" * 70)


def print_summary(results):
    """Print the analysis summary in a nice format"""
    summary = results['summary']
    
    print("\n")
    print("┌" + "─" * 68 + "┐")
    print("│" + " " * 20 + "📊 ANALYSIS SUMMARY" + " " * 28 + "│")
    print("├" + "─" * 68 + "┤")
    print(f"│  📁 Files analyzed:        {summary['files_analyzed']:<40}│")
    print(f"│  📦 Classes found:         {summary['total_classes']:<40}│")
    print(f"│  🔧 Functions found:       {summary['total_functions']:<40}│")
    print(f"│  📥 Imports found:         {summary['total_imports']:<40}│")
    print(f"│  🔗 Call relationships:    {summary['total_calls']:<40}│")
    print("└" + "─" * 68 + "┘")


def print_most_called(results):
    """Print the most called functions (hot spots)"""
    most_called = results['summary']['most_called']
    
    print("\n")
    print("┌" + "─" * 68 + "┐")
    print("│" + " " * 15 + "🔥 MOST CALLED FUNCTIONS (Hot Spots)" + " " * 16 + "│")
    print("├" + "─" * 68 + "┤")
    
    for i, (func_name, count) in enumerate(most_called[:10], 1):
        # Truncate long function names
        display_name = func_name[:45] + "..." if len(func_name) > 45 else func_name
        print(f"│  {i:2d}. {display_name:<50} {count:>4}x │")
    
    print("└" + "─" * 68 + "┘")


def print_orchestrators(results):
    """Print functions that call many others (orchestrators)"""
    orchestrators = results['summary']['orchestrators']
    
    if not orchestrators:
        return
    
    print("\n")
    print("┌" + "─" * 68 + "┐")
    print("│" + " " * 12 + "🎯 TOP ORCHESTRATORS (Call Many Functions)" + " " * 12 + "│")
    print("├" + "─" * 68 + "┤")
    
    for i, (func_name, call_count) in enumerate(orchestrators[:10], 1):
        # Truncate long function names
        display_name = func_name[:42] + "..." if len(func_name) > 42 else func_name
        print(f"│  {i:2d}. {display_name:<45} calls {call_count:>3} others │")
    
    print("└" + "─" * 68 + "┘")


def print_sample_files(results):
    """Print sample of analyzed files"""
    entities = results['entities'][:10]
    
    print("\n")
    print("┌" + "─" * 68 + "┐")
    print("│" + " " * 18 + "📦 SAMPLE FILES (First 10)" + " " * 23 + "│")
    print("├" + "─" * 68 + "┤")
    
    for entity in entities:
        file_name = entity['file']
        # Truncate long file names
        if len(file_name) > 60:
            file_name = "..." + file_name[-57:]
        
        classes_count = len(entity['classes'])
        funcs_count = len(entity['functions'])
        imports_count = len(entity['imports'])
        
        print(f"│  📄 {file_name:<60} │")
        print(f"│      └─ {classes_count} classes, {funcs_count} functions, {imports_count} imports{' ' * (60 - len(f'{classes_count} classes, {funcs_count} functions, {imports_count} imports') - 7)}│")
    
    print("└" + "─" * 68 + "┘")


def print_key_classes(results):
    """Print key classes with most methods"""
    all_classes = []
    
    for entity in results['entities']:
        for cls in entity['classes']:
            all_classes.append({
                'name': cls['name'],
                'file': entity['file'],
                'methods': len(cls['methods']),
                'line': cls['line']
            })
    
    # Sort by number of methods
    all_classes.sort(key=lambda x: x['methods'], reverse=True)
    top_classes = all_classes[:10]
    
    if not top_classes:
        return
    
    print("\n")
    print("┌" + "─" * 68 + "┐")
    print("│" + " " * 16 + "🏛️  KEY CLASSES (Most Methods)" + " " * 20 + "│")
    print("├" + "─" * 68 + "┤")
    
    for i, cls in enumerate(top_classes, 1):
        cls_name = cls['name'][:35] + "..." if len(cls['name']) > 35 else cls['name']
        file_short = cls['file'][:35] + "..." if len(cls['file']) > 35 else cls['file']
        
        print(f"│  {i:2d}. {cls_name:<40} {cls['methods']:>3} methods │")
        print(f"│      └─ {file_short:<56} │")
    
    print("└" + "─" * 68 + "┘")


def save_results_to_json(results, output_dir="."):
    """Save detailed results to JSON files"""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Save entities
    with open(output_path / "entities.json", 'w', encoding='utf-8') as f:
        json.dump(results['entities'], f, indent=2)
    
    # Save summary
    with open(output_path / "summary.json", 'w', encoding='utf-8') as f:
        json.dump(results['summary'], f, indent=2)
    
    print("\n")
    print("┌" + "─" * 68 + "┐")
    print("│" + " " * 22 + "💾 SAVED TO FILES" + " " * 29 + "│")
    print("├" + "─" * 68 + "┤")
    print(f"│  ✓ entities.json  - All classes, functions, imports{' ' * 13}│")
    print(f"│  ✓ summary.json   - Statistics and insights{' ' * 21}│")
    print("└" + "─" * 68 + "┘")


# ============================================================================
# PART 3: MAIN EXECUTION - Put it all together
# ============================================================================

def main():
    """Main function to run the analyzer"""
    print_banner()
    
    # Default path - change this to your ERPNext directory
    default_path = r"C:\Users\Shivansh\OneDrive\Desktop\ErpNext_Code_Analyzer\erpnext\accounts"
    
    print("\n📂 Enter the directory path to analyze:")
    print(f"   (Press Enter to use: {default_path})")
    print()
    
    user_input = input("Path: ").strip()
    
    # Use default if no input
    if not user_input:
        directory_path = default_path
    else:
        directory_path = user_input
    
    # Remove quotes if user copied path with quotes
    directory_path = directory_path.strip('"').strip("'")
    
    print(f"\n🎯 Analyzing: {directory_path}")
    
    # Run the analysis
    results = analyze_directory(directory_path)
    
    if results is None:
        print("\n❌ Analysis failed. Please check the path and try again.")
        return
    
    # Display results
    print_summary(results)
    print_most_called(results)
    print_orchestrators(results)
    print_key_classes(results)
    print_sample_files(results)
    
    # Ask if user wants to save results
    print("\n")
    print("─" * 70)
    save = input("💾 Save detailed results to JSON files? (y/n): ").strip().lower()
    
    if save == 'y' or save == 'yes':
        save_results_to_json(results, output_dir="analysis_output")
    
    print("\n✨ Analysis complete! Thanks for using the Code Analyzer!")
    print("═" * 70)
    print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Analysis interrupted by user. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        sys.exit(1)