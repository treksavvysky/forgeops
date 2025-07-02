import subprocess
import sys
import os

# Determine the correct path to main.py, assuming it's in the parent directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN_SCRIPT_PATH = os.path.join(BASE_DIR, "main.py")

def print_header(title):
    print("\n" + "=" * 70)
    print(f"ForgeOps - Issue Tracker Tutorial: {title}")
    print("=" * 70)

def wait_for_user(prompt="\nPress Enter to continue..."):
    input(prompt)

def run_command(command_args, interactive=False, user_input=None):
    full_command = [sys.executable, MAIN_SCRIPT_PATH] + command_args
    print(f"\n▶️  Executing: {' '.join(full_command)}")
    if interactive:
        print("   (This command is interactive. Please follow the prompts in your terminal.)")
        process = subprocess.Popen(full_command, stdin=subprocess.PIPE)
        # For interactive, we let it run. If specific input is needed before interaction:
        if user_input:
            try:
                process.communicate(input=user_input.encode(), timeout=15) # Example timeout
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
                print("   (Interactive command timed out or completed.)")
        else:
            process.wait() # Wait for the interactive process to complete
        print("   (Interactive command session finished.)")
        return "Interactive command executed. Please observe the output above.", ""
    else:
        try:
            result = subprocess.run(full_command, capture_output=True, text=True, check=False, timeout=30)
            print("\n--- Output ---")
            if result.stdout:
                print(result.stdout.strip())
            if result.stderr:
                print("--- Errors (if any) ---")
                print(result.stderr.strip())
            print("--------------")
            return result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            print("   Command timed out!")
            return "Error: Command timed out.", "Timeout"
        except Exception as e:
            print(f"   Error executing command: {e}")
            return f"Error: {e}", str(e)


def main_tutorial():
    print_header("Introduction")
    print("Welcome to the ForgeOps Issue Tracker tutorial!")
    print("This tutorial will guide you through the basic commands to manage repositories and issues.")
    print("At each step, we will explain a command, show you how to use it,")
    print("and then THE SCRIPT WILL EXECUTE THE COMMAND FOR YOU and display its output.")
    print(f"We will be using the main script located at: {MAIN_SCRIPT_PATH}")
    if not os.path.exists(MAIN_SCRIPT_PATH):
        print(f"\nERROR: main.py not found at {MAIN_SCRIPT_PATH}")
        print("Please ensure the tutorial is in the 'tutorials' directory and 'main.py' is in the parent directory.")
        return
    wait_for_user()

    # Step 1: Help Command
    print_header("Getting Help")
    print("The 'help' command displays all available commands and how to use them.")
    run_command(["help"])
    wait_for_user()

    # Step 2: List Repositories (initially empty)
    print_header("Listing Repositories (Initial)")
    print("Repositories are used to group your issues (e.g., by project).")
    print("Let's see what repositories are currently registered.")
    run_command(["list-repos"])
    print("\nIf this is your first time running the system, you'll likely see 'No repositories found'.")
    wait_for_user()

    # Step 3: Add a Repository
    print_header("Adding a Repository")
    print("Now, let's add your first repository.")
    repo_name1 = input("Enter a name for your first repository (e.g., 'my-first-project'): ").strip()
    if not repo_name1:
        repo_name1 = "my-first-project"
        print(f"No input, using default: {repo_name1}")
    run_command(["add-repo", repo_name1])

    print("\nLet's add another one.")
    repo_name2 = input("Enter a name for your second repository (e.g., 'web-app'): ").strip()
    if not repo_name2:
        repo_name2 = "web-app"
        print(f"No input, using default: {repo_name2}")
    run_command(["add-repo", repo_name2])
    wait_for_user()

    # Step 4: List Repositories (after adding)
    print_header("Listing Repositories (Updated)")
    print("Now that you've added some repositories, let's list them again.")
    run_command(["list-repos"])
    print(f"\nYou should see '{repo_name1}' and '{repo_name2}' listed above.")
    wait_for_user()

    # Step 5: Create an Issue
    print_header("Creating an Issue")
    print("Issues are the core of the tracker. Let's create one.")
    print("The 'create-issue' command is interactive. The tutorial will launch it,")
    print("and you will need to follow the prompts IN YOUR TERMINAL to enter the details.")
    print("Suggested details for your first issue:")
    print(f"  - Title: 'Implement login page'")
    print(f"  - Repository name: '{repo_name1}' (or choose another)")
    print(f"  - Description: 'Users need to be able to log in using email and password.'")
    print("\nWhen prompted 'Create this issue? (Y/n):', type 'Y' and press Enter.")
    wait_for_user("Press Enter to launch the interactive 'create-issue' command...")
    run_command(["create-issue"], interactive=True)
    print("\nHopefully, you saw a success message for issue creation!")
    print("Take note of the ISSUE-ID (e.g., ISSUE-001, ISSUE-002, etc.) assigned to your issue.")
    print("It will be printed by the 'create-issue' command upon success.")
    wait_for_user()

    # Step 6: List Issues
    print_header("Listing Issues")
    print("After creating an issue, you can list all issues to see it.")
    run_command(["list-issues"])
    print("\nYou should see your newly created issue listed above.")
    print("Make sure you can identify its ISSUE-ID from the output.")
    wait_for_user()

    # Step 7: View a Specific Issue
    print_header("Viewing a Specific Issue")
    print("To see all details of a specific issue, you use the 'view-issue' command")
    print("followed by its ISSUE-ID.")
    issue_id_to_view = input("Enter the ISSUE-ID of the issue you just created (e.g., ISSUE-001): ").strip().upper()
    if not issue_id_to_view:
        print("No ISSUE-ID entered. Skipping view command. Please try to note it next time.")
    else:
        run_command(["view-issue", issue_id_to_view])
    wait_for_user()

    # Step 8: List Issues by Repository
    print_header("Filtering Issues by Repository")
    print("If you have many issues, you can filter them by repository.")
    print(f"Let's try to list issues only for the '{repo_name1}' repository.")
    run_command(["list-issues", "--repo", repo_name1])
    print(f"\nThe output above should only show issues belonging to '{repo_name1}'.")
    wait_for_user()

    print_header("Tutorial Complete!")
    print("Congratulations! You've learned the basics of the ForgeOps Issue Tracker.")
    print("This script executed the commands for you and showed their output.")
    print("You can run 'python main.py help' in your terminal if you forget a command.")
    print("The repositories and issues you created during this tutorial still exist.")
    print("You can manage them using the CLI.")
    print("Happy coding!")

if __name__ == "__main__":
    main_tutorial()
