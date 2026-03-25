import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, act, waitFor } from "@testing-library/react";

// Mock the api module before importing AlertBell
vi.mock("@/lib/api", () => ({
  getAlerts: vi.fn(),
  getUnreadAlertCount: vi.fn(),
  markAlertRead: vi.fn(),
  markAllAlertsRead: vi.fn(),
}));

// Import mocks after vi.mock
const apiMocks = await import("@/lib/api");
const mockGetUnreadAlertCount = vi.mocked(apiMocks.getUnreadAlertCount);
const mockGetAlerts = vi.mocked(apiMocks.getAlerts);
const mockMarkAlertRead = vi.mocked(apiMocks.markAlertRead);
const mockMarkAllAlertsRead = vi.mocked(apiMocks.markAllAlertsRead);

const { AlertBell } = await import("../alert-bell");

beforeEach(() => {
  vi.clearAllMocks();
  mockGetUnreadAlertCount.mockResolvedValue({ count: 0 });
  mockGetAlerts.mockResolvedValue([]);
  mockMarkAlertRead.mockResolvedValue({ message: "ok" });
  mockMarkAllAlertsRead.mockResolvedValue({ message: "ok" });
});

describe("AlertBell", () => {
  it("renders the bell button", async () => {
    render(<AlertBell />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Alerts" })).toBeInTheDocument();
    });
  });

  it("shows unread count badge when count > 0", async () => {
    mockGetUnreadAlertCount.mockResolvedValue({ count: 5 });

    render(<AlertBell />);

    await waitFor(() => {
      expect(screen.getByText("5")).toBeInTheDocument();
    });
  });

  it("does not show badge when count is 0", async () => {
    mockGetUnreadAlertCount.mockResolvedValue({ count: 0 });

    render(<AlertBell />);

    // Wait for the effect to run
    await waitFor(() => {
      expect(mockGetUnreadAlertCount).toHaveBeenCalled();
    });

    // There should be no badge number
    expect(screen.queryByText("0")).not.toBeInTheDocument();
  });

  it("shows 99+ for counts over 99", async () => {
    mockGetUnreadAlertCount.mockResolvedValue({ count: 150 });

    render(<AlertBell />);

    await waitFor(() => {
      expect(screen.getByText("99+")).toBeInTheDocument();
    });
  });

  it("opens dropdown and shows alerts on click", async () => {
    mockGetUnreadAlertCount.mockResolvedValue({ count: 1 });
    mockGetAlerts.mockResolvedValue([
      {
        id: 1,
        alert_type: "scan",
        symbol: "RELIANCE",
        title: "New PPC Signal",
        message: "RELIANCE triggered PPC",
        severity: "info",
        is_read: false,
        created_at: new Date().toISOString().replace("Z", ""),
        data: null,
      },
    ]);

    render(<AlertBell />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Alerts" })).toBeInTheDocument();
    });

    await act(async () => {
      screen.getByRole("button", { name: "Alerts" }).click();
    });

    await waitFor(() => {
      expect(screen.getByText("New PPC Signal")).toBeInTheDocument();
      expect(screen.getByText("RELIANCE")).toBeInTheDocument();
    });
  });

  it("shows empty state when no alerts", async () => {
    mockGetAlerts.mockResolvedValue([]);

    render(<AlertBell />);

    await act(async () => {
      screen.getByRole("button", { name: "Alerts" }).click();
    });

    await waitFor(() => {
      expect(screen.getByText("No alerts yet")).toBeInTheDocument();
    });
  });

  it("handles fetch error gracefully", async () => {
    mockGetUnreadAlertCount.mockRejectedValue(new Error("Network error"));
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    render(<AlertBell />);

    // Should not crash
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Alerts" })).toBeInTheDocument();
    });

    consoleSpy.mockRestore();
  });

  it("shows Mark all read button when there are unread alerts", async () => {
    mockGetUnreadAlertCount.mockResolvedValue({ count: 3 });
    mockGetAlerts.mockResolvedValue([
      {
        id: 1,
        alert_type: "scan",
        symbol: null,
        title: "Test Alert",
        message: "Test message",
        severity: "warning",
        is_read: false,
        created_at: new Date().toISOString().replace("Z", ""),
        data: null,
      },
    ]);

    render(<AlertBell />);

    await waitFor(() => {
      expect(screen.getByText("3")).toBeInTheDocument();
    });

    await act(async () => {
      screen.getByRole("button", { name: "Alerts" }).click();
    });

    await waitFor(() => {
      expect(screen.getByText("Mark all read")).toBeInTheDocument();
    });
  });

  it("closes dropdown on second click", async () => {
    mockGetAlerts.mockResolvedValue([
      {
        id: 1,
        alert_type: "scan",
        symbol: null,
        title: "Visible Alert",
        message: "msg",
        severity: "info",
        is_read: true,
        created_at: new Date().toISOString().replace("Z", ""),
        data: null,
      },
    ]);

    render(<AlertBell />);

    // Open
    await act(async () => {
      screen.getByRole("button", { name: "Alerts" }).click();
    });

    await waitFor(() => {
      expect(screen.getByText("Visible Alert")).toBeInTheDocument();
    });

    // Close by clicking bell again
    await act(async () => {
      screen.getByRole("button", { name: "Alerts" }).click();
    });

    expect(screen.queryByText("Visible Alert")).not.toBeInTheDocument();
  });
});
