export const wait = async (delay: number) => new Promise<void>((resolve) => {
  setTimeout(resolve, delay);
});
