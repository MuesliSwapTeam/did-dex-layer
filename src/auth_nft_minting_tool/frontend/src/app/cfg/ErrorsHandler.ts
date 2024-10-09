type Handler = (err: {error: string; stackTrace?: string}) => void;

class ErrorsHandler {
  private handler!: Handler;

  setErrorHandler(handler: Handler) {
    this.handler = handler;
  }

  handleError(err: {error: string; stackTrace?: string}) {
    if (this.handler !== undefined) {
      console.log('i handle', err);
      this.handler(err);
    }
    throw err;
  }
}

export const errorsHandler = new ErrorsHandler();
