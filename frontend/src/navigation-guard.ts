type NavigationBlocker = (destination: string) => void;

let blocker: NavigationBlocker | null = null;
let bypassDestination: string | null = null;

export function registerNavigationBlocker(next: NavigationBlocker): () => void {
  blocker = next;
  return () => {
    if (blocker === next) blocker = null;
  };
}

export function shouldBlockNavigation(destination: string): boolean {
  if (bypassDestination === destination) {
    bypassDestination = null;
    return false;
  }
  if (!blocker) return false;
  blocker(destination);
  return true;
}

export function navigateWithoutBlocking(destination: string): void {
  bypassDestination = destination;
  location.hash = destination;
}
