"""
NLU Service Main Entry Point

This module provides the main entry point for the NLU service.
The actual service logic has been moved to service_manager.py for better organization.
"""
import asyncio
import signal
import sys

from event_bus_framework import get_logger
from .service_manager import NLUServiceManager

# Set up logging
logger = get_logger("nlu_service.main")


def setup_signal_handlers(service_manager: NLUServiceManager) -> None:
    """Setup signal handlers for graceful shutdown"""
    def signal_handler(signum, frame):
        logger.debug(f"Received signal {signum}, shutting down...")
        service_manager.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def main_async() -> None:
    """Main async entry point for the NLU service"""
    try:
        # Create service manager
        service_manager = NLUServiceManager()
        
        # Setup signal handlers for graceful shutdown
        setup_signal_handlers(service_manager)
        
        # Start the service
        await service_manager.start_async()
        
        # Keep the service running
        logger.debug("NLU Service is running. Press Ctrl+C to stop.")
        
        try:
            while service_manager.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.debug("Received keyboard interrupt")
        
        # Stop the service
        await service_manager.stop_async()
        
    except Exception as e:
        logger.error(f"Fatal error in NLU Service: {e}")
        sys.exit(1)


def main() -> None:
    """Main entry point for the NLU service"""
    try:
        # Run the async main function
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.debug("Service interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 