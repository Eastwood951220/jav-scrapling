import { Component } from "react";
import { Result, Button } from "antd";

interface Props {
  children: React.ReactNode;
}

interface State {
  error: Error | null;
}

/**
 * Catches unhandled render errors in the component tree and displays a
 * fallback UI with the error message and a retry button.
 */
export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  handleRetry = () => {
    this.setState({ error: null });
  };

  render() {
    if (this.state.error) {
      return (
        <Result
          status="error"
          title="页面发生错误"
          subTitle={this.state.error.message}
          extra={
            <Button type="primary" onClick={this.handleRetry}>
              重试
            </Button>
          }
        />
      );
    }

    return this.props.children;
  }
}
