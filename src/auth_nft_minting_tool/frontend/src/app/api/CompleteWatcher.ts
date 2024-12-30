import {wait} from "../../utils/TimeUtils";

export class CompleteWatcher {
  private isRunning = false;

  constructor(private check: () => Promise<boolean>, private onComplete: () => void, private delay = 5000) {
  }

  async start() {
    this.isRunning = true;
    let isComplete = false
    try {
      isComplete = await this.check();
      while (!isComplete && this.isRunning) {
        await wait(this.delay);
        if (this.isRunning) {
          isComplete = await this.check();
        }
      }
    } catch (e) {
      console.log(e);
      this.isRunning = false;
    }
    if (this.isRunning) {
      this.isRunning = false;
      if (isComplete) {
        this.onComplete();
      }
    }
  }

  stop() {
    this.isRunning = false;
  }
}
