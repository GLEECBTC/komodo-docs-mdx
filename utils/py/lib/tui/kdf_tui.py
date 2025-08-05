#!/usr/bin/env python3
"""
KDF Tools TUI - Terminal User Interface for Komodo DeFi Framework Tools

Provides an interactive interface for kdf_tools.py while maintaining scriptability.
Uses rich and textual libraries for modern terminal UI.
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

try:
    from textual.app import App, ComposeResult
    from textual.containers import Container, Horizontal, Vertical
    from textual.widgets import (
        Header, Footer, Button, Input, Select, Label, 
        DataTable, Static, TextArea, Checkbox
    )
    from textual.reactive import reactive
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table
    from rich.prompt import Prompt, Confirm
    from rich import print as rprint
except ImportError:
    print("TUI dependencies not installed. Install with: pip install textual rich")
    sys.exit(1)

# Add utils/py to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lib.constants.config import get_config
from lib.utils.logging_utils import get_logger


@dataclass
class CommandConfig:
    """Configuration for a command with its arguments."""
    name: str
    description: str
    category: str
    arguments: Dict[str, Any]
    required_args: List[str]
    optional_args: Dict[str, Any]
    
    def __init__(self, name: str, description: str, category: str, 
                 arguments: Optional[Dict[str, Any]] = None,
                 required_args: Optional[List[str]] = None,
                 optional_args: Optional[Dict[str, Any]] = None):
        self.name = name
        self.description = description
        self.category = category
        self.arguments = arguments or {}
        self.required_args = required_args or []
        self.optional_args = optional_args or {}


class KDFTUI:
    """Main TUI class for KDF Tools."""
    
    def __init__(self):
        self.config = get_config()
        self.logger = get_logger("kdf-tui")
        self.console = Console()
        
        # Initialize current branch
        self.current_branch = self._get_current_branch()
        
        # Define available commands
        self.commands = self._define_commands()
        
    def _get_current_branch(self) -> str:
        """Get the current KDF branch."""
        try:
            # Try to get branch from config
            if hasattr(self.config, 'kdf_branch') and self.config.kdf_branch:
                return self.config.kdf_branch
            
            # Fallback to checking git directly
            kdf_repo_path = Path(self.config.directories.kdf_repo_path) if hasattr(self.config, 'directories') else None
            if kdf_repo_path and kdf_repo_path.exists():
                import subprocess
                result = subprocess.run(
                    ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                    cwd=kdf_repo_path,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    return result.stdout.strip()
            
            return "dev"  # Default fallback
        except Exception as e:
            self.logger.warning(f"Could not determine current branch: {e}")
            return "dev"
    
    def _switch_branch(self, new_branch: str) -> bool:
        """Switch to a new KDF branch."""
        try:
            kdf_repo_path = Path(self.config.directories.kdf_repo_path) if hasattr(self.config, 'directories') else None
            if not kdf_repo_path or not kdf_repo_path.exists():
                self.console.print(f"[red]KDF repository not found at: {kdf_repo_path}[/red]")
                return False
            
            import subprocess
            
            # Stash any local changes
            subprocess.run(["git", "stash"], cwd=kdf_repo_path, check=True, capture_output=True)
            
            # Fetch latest changes
            subprocess.run(["git", "fetch", "origin"], cwd=kdf_repo_path, check=True, capture_output=True)
            
            # Check if branch exists
            local_exists = subprocess.run(
                ["git", "show-ref", "--verify", f"refs/heads/{new_branch}"],
                cwd=kdf_repo_path, capture_output=True
            ).returncode == 0
            
            remote_exists = subprocess.run(
                ["git", "show-ref", "--verify", f"refs/remotes/origin/{new_branch}"],
                cwd=kdf_repo_path, capture_output=True
            ).returncode == 0
            
            if not local_exists and not remote_exists:
                self.console.print(f"[red]Branch '{new_branch}' not found locally or on origin.[/red]")
                return False
            
            # Checkout branch
            if not local_exists and remote_exists:
                subprocess.run(["git", "checkout", "--track", f"origin/{new_branch}"], cwd=kdf_repo_path, check=True, capture_output=True)
            else:
                subprocess.run(["git", "checkout", new_branch], cwd=kdf_repo_path, check=True, capture_output=True)
            
            # Pull latest changes
            subprocess.run(["git", "pull", "origin", new_branch], cwd=kdf_repo_path, check=True, capture_output=True)
            
            self.current_branch = new_branch
            self.console.print(f"[green]Successfully switched to branch '{new_branch}'[/green]")
            return True
            
        except subprocess.CalledProcessError as e:
            self.console.print(f"[red]Git command failed: {e}[/red]")
            return False
        except Exception as e:
            self.console.print(f"[red]Error switching branch: {e}[/red]")
            return False
    
    def _show_branch_selection(self) -> Optional[str]:
        """Show branch selection menu."""
        self.console.clear()
        
        # Common branches
        common_branches = ["dev", "main", "master", "develop", "staging"]
        
        # Get available branches from git
        available_branches = []
        try:
            kdf_repo_path = Path(self.config.directories.kdf_repo_path) if hasattr(self.config, 'directories') else None
            if kdf_repo_path and kdf_repo_path.exists():
                import subprocess
                
                # Get local branches
                result = subprocess.run(
                    ["git", "branch", "--format=%(refname:short)"],
                    cwd=kdf_repo_path,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    local_branches = [b.strip() for b in result.stdout.strip().split('\n') if b.strip()]
                    available_branches.extend(local_branches)
                
                # Get remote branches
                result = subprocess.run(
                    ["git", "branch", "-r", "--format=%(refname:short)"],
                    cwd=kdf_repo_path,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    remote_branches = [b.strip().replace('origin/', '') for b in result.stdout.strip().split('\n') if b.strip() and 'origin/' in b]
                    available_branches.extend(remote_branches)
                
                # Remove duplicates and sort
                available_branches = sorted(list(set(available_branches)))
        except Exception as e:
            self.logger.warning(f"Could not get available branches: {e}")
        
        # Combine common and available branches
        all_branches = list(set(common_branches + available_branches))
        all_branches.sort()
        
        # Create branch selection table
        table = Table(title="Branch Selection", show_header=True, header_style="bold magenta")
        table.add_column("#", style="cyan", width=5)
        table.add_column("Branch", style="white", width=30)
        table.add_column("Status", style="green", width=20)
        
        for i, branch in enumerate(all_branches, 1):
            status = "Current" if branch == self.current_branch else "Available"
            style = "bold green" if branch == self.current_branch else "white"
            table.add_row(str(i), branch, status, style=style)
        
        self.console.print(table)
        self.console.print("\n")
        self.console.print("0. Back to Main Menu")
        self.console.print("Enter branch name manually (or number from list):")
        
        choice = self.console.input("\nSelect branch: ").strip()
        
        if choice == "0":
            return None
        
        try:
            # Try to parse as number
            choice_num = int(choice)
            if 1 <= choice_num <= len(all_branches):
                selected_branch = all_branches[choice_num - 1]
            else:
                self.console.print("[red]Invalid choice![/red]")
                return None
        except ValueError:
            # Treat as branch name
            selected_branch = choice
        
        # Switch to selected branch
        if self._switch_branch(selected_branch):
            return selected_branch
        else:
            self.console.input("\nPress Enter to continue...")
            return None
        
    def _define_commands(self) -> Dict[str, CommandConfig]:
        """Define all available commands with their configurations."""
        return {
            # Documentation Commands
            "scan-mdx": CommandConfig(
                name="scan-mdx",
                description="Scan MDX documentation files for method names",
                category="Documentation"
            ),
            "scan-rust": CommandConfig(
                name="scan-rust", 
                description="Scan KDF Rust repository for RPC methods",
                category="Documentation"
            ),
            "scan-existing-docs": CommandConfig(
                name="scan-existing-docs",
                description="Scan existing KDF documentation to extract method patterns",
                category="Documentation"
            ),
            "gap-analysis": CommandConfig(
                name="gap-analysis",
                description="Compare Rust methods with MDX documentation",
                category="Documentation"
            ),
            "map_methods": CommandConfig(
                name="map_methods",
                description="Generate a unified mapping of all method-related files",
                category="Documentation"
            ),
            
            # API Generation Commands
            "openapi": CommandConfig(
                name="openapi",
                description="Generate OpenAPI specs from MDX documentation",
                category="API Generation"
            ),
            "postman": CommandConfig(
                name="postman",
                description="Generate Postman collections from OpenAPI specs",
                category="API Generation"
            ),
            
            # Documentation Generation
            "sync": CommandConfig(
                name="sync",
                description="Bidirectional sync between MDX docs and Postman collections",
                category="Documentation Generation",
                required_args=["direction"],
                optional_args={
                    "--method-filter": "",
                    "--dry-run": False
                }
            ),
            
            # Container Commands
            "build-container": CommandConfig(
                name="build-container",
                description="Build the KDF container",
                category="Container"
            ),
            "start-container": CommandConfig(
                name="start-container",
                description="Start the KDF container",
                category="Container"
            ),
            "stop-container": CommandConfig(
                name="stop-container",
                description="Stop the KDF container",
                category="Container"
            ),
            
            # Analysis Commands
            "json-extract": CommandConfig(
                name="json-extract",
                description="Extract JSON examples from MDX files",
                category="Analysis",
                optional_args={
                    "--substitute-defaults": False
                }
            ),
            "get-kdf-responses": CommandConfig(
                name="get-kdf-responses",
                description="Get KDF responses for a given method",
                category="Analysis",
                optional_args={
                    "--method": "",
                    "--clean": False,
                    "--substitute-defaults": False
                }
            ),
            "extract-errors": CommandConfig(
                name="extract-errors",
                description="Extract error enums from KDF Rust codebase",
                category="Analysis"
            ),
            "review-draft-quality": CommandConfig(
                name="review-draft-quality",
                description="Compare generated documentation with live versions",
                category="Analysis"
            ),
            "v2-no-param-methods-report": CommandConfig(
                name="v2-no-param-methods-report",
                description="Generate a report of V2 methods that don't have parameters",
                category="Analysis"
            ),
            "report-error-responses": CommandConfig(
                name="report-error-responses",
                description="Generate a report of method requests that have error responses",
                category="Analysis"
            ),
            "get-json-example-method-paths": CommandConfig(
                name="get-json-example-method-paths",
                description="Get JSON example method paths",
                category="Analysis"
            ),
            
            # Documentation Generation
            "generate-docs": CommandConfig(
                name="generate-docs",
                description="Generate MDX documentation from templates for specified methods",
                category="Documentation Generation"
            ),
            
            # System Commands
            "balances": CommandConfig(
                name="balances",
                description="Get address and balance info for test coins",
                category="System",
                optional_args={
                    "--clean": False
                }
            ),
            "switch-kdf-branch": CommandConfig(
                name="switch-kdf-branch",
                description="Switch the KDF branch",
                category="System",
                required_args=["branch"]
            ),
            
            # Workflow Commands
            "walletconnect-workflow": CommandConfig(
                name="walletconnect-workflow",
                description="Interactive WalletConnect session management",
                category="Workflows"
            ),
            "trezor-workflow": CommandConfig(
                name="trezor-workflow", 
                description="Interactive Trezor device management",
                category="Workflows"
            )
        }
    
    def get_commands_by_category(self) -> Dict[str, List[CommandConfig]]:
        """Group commands by category."""
        categories = {}
        for cmd in self.commands.values():
            if cmd.category not in categories:
                categories[cmd.category] = []
            categories[cmd.category].append(cmd)
        return categories
    
    def show_main_menu(self):
        """Display the main menu."""
        self.console.clear()
        
        # Create main menu table with current branch in header
        table = Table(title=f"KDF Tools - Main Menu (Branch: {self.current_branch})", show_header=True, header_style="bold magenta")
        table.add_column("Category", style="cyan", width=20)
        table.add_column("Commands", style="white", width=60)
        table.add_column("Description", style="green", width=40)
        
        categories = self.get_commands_by_category()
        for category, commands in categories.items():
            cmd_names = ", ".join([cmd.name for cmd in commands])
            description = f"{len(commands)} command(s) available"
            table.add_row(category, cmd_names, description)
        
        self.console.print(table)
        self.console.print("\n")
        
        # Show navigation options with branch selection
        options = [
            "1. Browse by Category",
            "2. Search Commands", 
            "3. Quick Run (Common Commands)",
            "4. Switch KDF Branch",
            "5. Exit"
        ]
        
        for option in options:
            self.console.print(f"  {option}")
        
        return self.console.input("\nSelect an option (1-5): ").strip()
    
    def show_category_menu(self, category: str):
        """Display commands for a specific category."""
        self.console.clear()
        
        categories = self.get_commands_by_category()
        if category not in categories:
            self.console.print(f"[red]Category '{category}' not found![/red]")
            return None
        
        commands = categories[category]
        
        table = Table(title=f"Commands - {category}", show_header=True, header_style="bold magenta")
        table.add_column("#", style="cyan", width=5)
        table.add_column("Command", style="white", width=30)
        table.add_column("Description", style="green", width=50)
        
        for i, cmd in enumerate(commands, 1):
            table.add_row(str(i), cmd.name, cmd.description)
        
        self.console.print(table)
        self.console.print("\n")
        self.console.print("0. Back to Main Menu")
        
        choice = self.console.input(f"\nSelect a command (0-{len(commands)}): ").strip()
        
        try:
            choice_num = int(choice)
            if choice_num == 0:
                return None
            elif 1 <= choice_num <= len(commands):
                return commands[choice_num - 1]
            else:
                self.console.print("[red]Invalid choice![/red]")
                return None
        except ValueError:
            self.console.print("[red]Please enter a number![/red]")
            return None
    
    def configure_command(self, command: CommandConfig) -> Optional[Dict[str, Any]]:
        """Configure command arguments interactively."""
        self.console.clear()
        
        # Show command info
        self.console.print(Panel(
            f"[bold]Command:[/bold] {command.name}\n"
            f"[bold]Description:[/bold] {command.description}\n"
            f"[bold]Category:[/bold] {command.category}",
            title="Command Configuration",
            border_style="blue"
        ))
        
        # Show cancellation option
        self.console.print("[yellow]Press Ctrl+C to cancel configuration[/yellow]\n")
        
        # Collect arguments
        args = command.arguments.copy() if command.arguments else {}
        
        # Handle required arguments
        for arg in command.required_args:
            try:
                # Special handling for sync direction
                if command.name == "sync" and arg == "direction":
                    self.console.print("\n[bold]Select sync direction:[/bold]")
                    directions = [
                        ("1", "docs-to-postman", "Sync from MDX docs to Postman collections"),
                        ("2", "postman-to-docs", "Sync from Postman collections to MDX docs"),
                        ("3", "bidirectional", "Bidirectional sync between docs and collections")
                    ]
                    
                    for num, direction, description in directions:
                        self.console.print(f"  {num}. {direction} - {description}")
                    
                    while True:
                        choice = self.console.input("\nSelect direction (1-3): ").strip()
                        if choice in ["1", "2", "3"]:
                            value = directions[int(choice) - 1][1]
                            break
                        else:
                            self.console.print("[red]Invalid choice. Please enter 1, 2, or 3.[/red]")

                else:
                    # Default handling for other required arguments
                    value = self.console.input(f"Enter {arg}: ").strip()
                
                if not value:
                    self.console.print(f"[red]{arg} is required![/red]")
                    self.console.print("[yellow]Configuration cancelled due to missing required argument.[/yellow]")
                    return None
                args[arg] = value
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Configuration cancelled by user.[/yellow]")
                return None
        
        # Handle optional arguments
        for arg, default in command.optional_args.items():
            try:
                # Special handling for get-kdf-responses method selection
                if command.name == "get-kdf-responses" and arg == "--method":
                    self.console.print("\n[bold]Select method or method group:[/bold]")
                    
                    # Import method groups
                    try:
                        from lib.constants.method_groups import KdfMethods
                        
                        # Define method groups with descriptions
                        method_groups = [
                            ("1", "trezor", "Trezor device methods (connection, activation, wallet tasks)"),
                            ("2", "walletconnect", "WalletConnect session management and EVM activation"),
                            ("3", "balances", "Balance-related queries (legacy + task-based)"),
                            ("4", "withdraws", "Withdrawal and transaction methods"),
                            ("5", "no_params_v2", "V2 methods that require explicit empty params object"),
                            ("6", "no_auth", "Methods that don't require authentication"),
                            ("7", "removed", "Deprecated/removed methods"),
                            ("8", "custom", "Enter a custom method name")
                        ]
                        
                        for num, group_name, description in method_groups:
                            method_count = len(getattr(KdfMethods, group_name, []))
                            self.console.print(f"  {num}. {group_name} ({method_count} methods) - {description}")
                        
                        while True:
                            choice = self.console.input(f"\nSelect option (1-{len(method_groups)}): ").strip()
                            if choice.isdigit() and 1 <= int(choice) <= len(method_groups):
                                selected_group = method_groups[int(choice) - 1][1]
                                
                                if selected_group == "custom":
                                    # Allow custom method input
                                    value = self.console.input("Enter custom method name: ").strip()
                                    if not value:
                                        self.console.print("[red]Method name is required![/red]")
                                        continue
                                else:
                                    # Get methods from the selected group
                                    methods = getattr(KdfMethods, selected_group, [])
                                    if not methods:
                                        self.console.print(f"[red]No methods found in group '{selected_group}'[/red]")
                                        continue
                                    
                                    # Show methods in the group for selection
                                    self.console.print(f"\n[bold]Methods in '{selected_group}' group:[/bold]")
                                    self.console.print(f"  0. ALL ({len(methods)} methods)")
                                    for i, method in enumerate(methods, 1):
                                        self.console.print(f"  {i}. {method}")
                                    
                                    method_choice = self.console.input(f"\nSelect method (0-{len(methods)}): ").strip()
                                    if method_choice == "0":
                                        # User selected ALL methods
                                        value = ",".join(methods)  # Join all methods with comma
                                    elif method_choice.isdigit() and 1 <= int(method_choice) <= len(methods):
                                        value = methods[int(method_choice) - 1]
                                    else:
                                        self.console.print("[red]Invalid method choice![/red]")
                                        continue
                                break
                            else:
                                self.console.print(f"[red]Invalid choice. Please enter 1-{len(method_groups)}.[/red]")
                    except ImportError:
                        # Fallback to simple input if method_groups import fails
                        self.console.print("[yellow]Warning: Could not load method groups. Using simple input.[/yellow]")
                        value = self.console.input(f"Enter {arg} (default: {default}): ").strip()
                        value = value if value else default
                elif isinstance(default, bool):
                    # Boolean argument
                    use_default = Confirm.ask(
                        f"Use {arg}? (default: {default})",
                        default=default
                    )
                    args[arg] = use_default
                else:
                    # String/number argument
                    value = self.console.input(f"Enter {arg} (default: {default}): ").strip()
                    args[arg] = value if value else default
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Configuration cancelled by user.[/yellow]")
                return None
        
        return args
    
    def execute_command(self, command: CommandConfig, args: Dict[str, Any]):
        """Execute the command with the given arguments."""
        self.console.clear()
        
        # Build command line with absolute path to kdf_tools.py
        workspace_root = Path(self.config.directories.workspace_root) if hasattr(self.config, 'directories') else Path.cwd().parent.parent
        kdf_tools_path = workspace_root / "utils" / "py" / "kdf_tools.py"
        cmd_parts = ["python", str(kdf_tools_path), command.name]
        
        # Add arguments
        for key, value in args.items():
            if isinstance(value, bool):
                if value:
                    cmd_parts.append(key)
            else:
                # For required arguments (positional), only add the value
                # For optional arguments (flags), add both key and value
                if key in command.required_args:
                    cmd_parts.append(str(value))
                else:
                    cmd_parts.extend([key, str(value)])
        
        cmd_line = " ".join(cmd_parts)
        
        self.console.print(Panel(
            f"[bold]Executing:[/bold]\n{cmd_line}",
            title="Command Execution",
            border_style="green"
        ))
        
        # Execute the command
        try:
            import subprocess
            result = subprocess.run(cmd_parts, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.console.print("[green]✅ Command executed successfully![/green]")
                if result.stdout:
                    self.console.print("\n[bold]Output:[/bold]")
                    self.console.print(result.stdout)
                self.console.print("\n[green]Press Enter to return to main menu...[/green]")
            else:
                self.console.print("[red]❌ Command failed![/red]")
                if result.stderr:
                    self.console.print("\n[bold]Error:[/bold]")
                    self.console.print(result.stderr)
                self.console.print("\n[red]Press Enter to return to main menu...[/red]")
                    
        except Exception as e:
            self.console.print(f"[red]❌ Error executing command: {e}[/red]")
            self.console.print("\n[red]Press Enter to return to main menu...[/red]")
        
        self.console.input("")
    
    def execute_workflow(self, command: CommandConfig, args: Dict[str, Any]):
        """Execute workflow commands that launch their own TUIs."""
        self.console.clear()
        
        if command.name == "walletconnect-workflow":
            self._launch_walletconnect_workflow()
        elif command.name == "trezor-workflow":
            self._launch_trezor_workflow()
        else:
            self.console.print(f"[red]Unknown workflow: {command.name}[/red]")
            self.console.print("\n[red]Press Enter to return to main menu...[/red]")
            self.console.input("")
    
    def _launch_walletconnect_workflow(self):
        """Launch the WalletConnect TUI."""
        self.console.print(Panel(
            "[bold]Launching WalletConnect TUI...[/bold]\n"
            "This will open an interactive interface for managing WalletConnect sessions.",
            title="WalletConnect Workflow",
            border_style="blue"
        ))
        
        try:
            import subprocess
            import sys
            from pathlib import Path
            
            # Get the path to the walletconnect.py script
            script_path = Path(__file__).parent.parent.parent / "tui" / "walletconnect.py"
            
            if not script_path.exists():
                self.console.print(f"[red]WalletConnect TUI not found at: {script_path}[/red]")
                self.console.input("\nPress Enter to continue...")
                return
            
            # Launch the WalletConnect TUI
            result = subprocess.run([sys.executable, str(script_path)], 
                                 capture_output=False, text=True)
            
            if result.returncode != 0:
                self.console.print("[red]WalletConnect TUI exited with errors[/red]")
                
        except Exception as e:
            self.console.print(f"[red]Error launching WalletConnect TUI: {e}[/red]")
        
        self.console.print("\n[green]Press Enter to return to main menu...[/green]")
        self.console.input("")
    
    def _launch_trezor_workflow(self):
        """Launch the Trezor TUI."""
        self.console.print(Panel(
            "[bold]Launching Trezor TUI...[/bold]\n"
            "This will open an interactive interface for managing Trezor devices.",
            title="Trezor Workflow", 
            border_style="blue"
        ))
        
        try:
            import subprocess
            import sys
            from pathlib import Path
            
            # Get the path to the trezor.py script
            script_path = Path(__file__).parent.parent.parent / "tui" / "trezor.py"
            
            if not script_path.exists():
                self.console.print(f"[red]Trezor TUI not found at: {script_path}[/red]")
                self.console.input("\nPress Enter to continue...")
                return
            
            # Launch the Trezor TUI
            result = subprocess.run([sys.executable, str(script_path)], 
                                 capture_output=False, text=True)
            
            if result.returncode != 0:
                self.console.print("[red]Trezor TUI exited with errors[/red]")
                
        except Exception as e:
            self.console.print(f"[red]Error launching Trezor TUI: {e}[/red]")
        
        self.console.print("\n[green]Press Enter to return to main menu...[/green]")
        self.console.input("")
    
    def show_quick_run_menu(self):
        """Show quick run menu for common commands."""
        self.console.clear()
        
        quick_commands = [
            ("scan-mdx", "Scan MDX documentation"),
            ("scan-rust", "Scan Rust repository"),
            ("gap-analysis", "Compare Rust vs MDX"),
            ("openapi", "Generate OpenAPI specs"),
            ("postman", "Generate Postman collections"),
            ("sync", "Bidirectional sync"),
            ("build-container", "Build KDF container"),
            ("start-container", "Start KDF container")
        ]
        
        table = Table(title="Quick Run - Common Commands", show_header=True, header_style="bold magenta")
        table.add_column("#", style="cyan", width=5)
        table.add_column("Command", style="white", width=30)
        table.add_column("Description", style="green", width=40)
        
        for i, (cmd_name, description) in enumerate(quick_commands, 1):
            table.add_row(str(i), cmd_name, description)
        
        self.console.print(table)
        self.console.print("\n")
        self.console.print("0. Back to Main Menu")
        
        choice = self.console.input(f"\nSelect a command (0-{len(quick_commands)}): ").strip()
        
        try:
            choice_num = int(choice)
            if choice_num == 0:
                return None
            elif 1 <= choice_num <= len(quick_commands):
                cmd_name = quick_commands[choice_num - 1][0]
                return self.commands.get(cmd_name)
            else:
                self.console.print("[red]Invalid choice![/red]")
                return None
        except ValueError:
            self.console.print("[red]Please enter a number![/red]")
            return None
    
    def search_commands(self, query: str) -> List[CommandConfig]:
        """Search commands by name or description."""
        query = query.lower()
        results = []
        
        for cmd in self.commands.values():
            if (query in cmd.name.lower() or 
                query in cmd.description.lower() or
                query in cmd.category.lower()):
                results.append(cmd)
        
        return results
    
    def show_search_results(self, results: List[CommandConfig]):
        """Display search results."""
        if not results:
            self.console.print("[yellow]No commands found matching your search.[/yellow]")
            return None
        
        table = Table(title="Search Results", show_header=True, header_style="bold magenta")
        table.add_column("#", style="cyan", width=5)
        table.add_column("Command", style="white", width=30)
        table.add_column("Category", style="blue", width=20)
        table.add_column("Description", style="green", width=40)
        
        for i, cmd in enumerate(results, 1):
            table.add_row(str(i), cmd.name, cmd.category, cmd.description)
        
        self.console.print(table)
        self.console.print("\n")
        self.console.print("0. Back to Main Menu")
        
        choice = self.console.input(f"\nSelect a command (0-{len(results)}): ").strip()
        
        try:
            choice_num = int(choice)
            if choice_num == 0:
                return None
            elif 1 <= choice_num <= len(results):
                return results[choice_num - 1]
            else:
                self.console.print("[red]Invalid choice![/red]")
                return None
        except ValueError:
            self.console.print("[red]Please enter a number![/red]")
            return None
    
    def run(self):
        """Main TUI loop."""
        while True:
            try:
                choice = self.show_main_menu()
                
                if choice == "1":
                    # Browse by Category
                    categories = list(self.get_commands_by_category().keys())
                    
                    self.console.clear()
                    self.console.print("Available Categories:")
                    for i, category in enumerate(categories, 1):
                        self.console.print(f"  {i}. {category}")
                    self.console.print("  0. Back to Main Menu")
                    
                    cat_choice = self.console.input(f"\nSelect category (0-{len(categories)}): ").strip()
                    
                    try:
                        cat_num = int(cat_choice)
                        if cat_num == 0:
                            continue
                        elif 1 <= cat_num <= len(categories):
                            selected_category = categories[cat_num - 1]
                            selected_command = self.show_category_menu(selected_category)
                            
                            if selected_command:
                                if selected_command.category == "Workflows":
                                    # Workflow commands don't need configuration
                                    self.execute_workflow(selected_command, {})
                                else:
                                    args = self.configure_command(selected_command)
                                    if args is not None:
                                        self.execute_command(selected_command, args)
                                    else:
                                        self.console.print("[yellow]Command configuration cancelled or incomplete.[/yellow]")
                                        self.console.input("\nPress Enter to continue...")
                        else:
                            self.console.print("[red]Invalid choice![/red]")
                            self.console.input("\nPress Enter to continue...")
                    except ValueError:
                        self.console.print("[red]Please enter a number![/red]")
                        self.console.input("\nPress Enter to continue...")
                
                elif choice == "2":
                    # Search Commands
                    query = self.console.input("Enter search term: ").strip()
                    if query:
                        results = self.search_commands(query)
                        selected_command = self.show_search_results(results)
                        
                        if selected_command:
                            if selected_command.category == "Workflows":
                                # Workflow commands don't need configuration
                                self.execute_workflow(selected_command, {})
                            else:
                                args = self.configure_command(selected_command)
                                if args is not None:
                                    self.execute_command(selected_command, args)
                                else:
                                    self.console.print("[yellow]Command configuration cancelled or incomplete.[/yellow]")
                                    self.console.input("\nPress Enter to continue...")
                
                elif choice == "3":
                    # Quick Run
                    selected_command = self.show_quick_run_menu()
                    
                    if selected_command:
                        if selected_command.category == "Workflows":
                            # Workflow commands don't need configuration
                            self.execute_workflow(selected_command, {})
                        else:
                            # Use default arguments for quick run
                            args = selected_command.optional_args.copy() if selected_command.optional_args else {}
                            self.execute_command(selected_command, args)
                
                elif choice == "4":
                    # Switch Branch
                    new_branch = self._show_branch_selection()
                    if new_branch:
                        # Re-define commands with the new branch
                        self.commands = self._define_commands()
                        self.current_branch = new_branch
                        self.console.print(f"[green]Switched to branch: {new_branch}[/green]")
                        self.show_main_menu() # Re-display main menu with new branch
                
                elif choice == "5":
                    # Exit
                    self.console.print("[green]Goodbye![/green]")
                    break
                
                else:
                    self.console.print("[red]Invalid choice![/red]")
                    self.console.input("\nPress Enter to continue...")
                    
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Interrupted by user. Exiting...[/yellow]")
                break
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/red]")
                self.console.input("\nPress Enter to continue...")


def main():
    """Main entry point for the TUI."""
    try:
        tui = KDFTUI()
        tui.run()
    except Exception as e:
        print(f"Error starting TUI: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 