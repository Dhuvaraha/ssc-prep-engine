import { Component, ReactNode } from "react";

type Props = { children: ReactNode };
type State = { failed: boolean };

export default class AppErrorBoundary extends Component<Props, State> {
  state: State = {failed: false};

  static getDerivedStateFromError(): State {
    return {failed: true};
  }

  componentDidCatch(error: unknown) {
    console.error("SSC Prep Engine render error", error);
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <main className="fatalErrorShell">
        <section>
          <p className="eyebrow">Something went wrong</p>
          <h1>This screen could not be rendered.</h1>
          <p>Your saved progress is not deleted. Reload the app or return to the dashboard.</p>
          <div>
            <button onClick={() => window.location.reload()}>Reload</button>
            <a href="/">Dashboard</a>
          </div>
        </section>
      </main>
    );
  }
}
