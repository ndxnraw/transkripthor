"""Stable Windows source/frozen entry point."""
if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    from ndtranskripthor.presentation.prepis import main
    main()
