"""
Entry point for FireflyTX shell.

Usage:
    python -m fireflytx.shell
"""

import sys


def main():
    """Main entry point for the shell."""
    try:
        from .core.shell import FireflyTXShell
        
        shell = FireflyTXShell()
        shell.run()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error starting shell: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

