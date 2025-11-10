import threading 
import uvicorn
import contextlib
import time

class Server(uvicorn.Server):
    def install_signal_handlers(self):
        pass # so we can manage shutdown ourselves
    @contextlib.contextmanager
    def run_in_thread(self):
        thread = threading.Thread(target = self.run)
        thread.start()
        try:
            while not self.started:
                time.sleep(0.001)
            yield
        finally:
            self.should_exit = True
            thread.join()