import { Suspense, lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import RouteFallback from "./components/RouteFallback";
import Login from "./pages/Login";

// Login and Layout stay eager — they are the first thing painted. Every other
// page is fetched on demand, so signing in no longer costs the whole app.
const Analytics = lazy(() => import("./pages/Analytics"));
const Billing = lazy(() => import("./pages/Billing"));
const Broadcast = lazy(() => import("./pages/Broadcast"));
const Calendar = lazy(() => import("./pages/Calendar"));
const ConversationView = lazy(() => import("./pages/ConversationView"));
const Inbox = lazy(() => import("./pages/Inbox"));
const Permissions = lazy(() => import("./pages/Permissions"));
const Programmes = lazy(() => import("./pages/Programmes"));
const ReportCards = lazy(() => import("./pages/ReportCards"));
const Staff = lazy(() => import("./pages/Staff"));
const Tickets = lazy(() => import("./pages/Tickets"));

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/inbox" replace />} />
        <Route
          path="inbox"
          element={
            <Suspense fallback={<RouteFallback />}>
              <Inbox />
            </Suspense>
          }
        />
        <Route
          path="conversations/:conversationId"
          element={
            <Suspense fallback={<RouteFallback />}>
              <ConversationView />
            </Suspense>
          }
        />
        <Route
          path="tickets"
          element={
            <Suspense fallback={<RouteFallback />}>
              <Tickets />
            </Suspense>
          }
        />
        <Route
          path="billing"
          element={
            <Suspense fallback={<RouteFallback />}>
              <Billing />
            </Suspense>
          }
        />
        <Route
          path="programmes"
          element={
            <Suspense fallback={<RouteFallback />}>
              <Programmes />
            </Suspense>
          }
        />
        <Route
          path="broadcast"
          element={
            <Suspense fallback={<RouteFallback />}>
              <Broadcast />
            </Suspense>
          }
        />
        <Route
          path="calendar"
          element={
            <Suspense fallback={<RouteFallback />}>
              <Calendar />
            </Suspense>
          }
        />
        <Route
          path="permissions"
          element={
            <Suspense fallback={<RouteFallback />}>
              <Permissions />
            </Suspense>
          }
        />
        <Route
          path="report-cards"
          element={
            <Suspense fallback={<RouteFallback />}>
              <ReportCards />
            </Suspense>
          }
        />
        <Route
          path="staff"
          element={
            <Suspense fallback={<RouteFallback />}>
              <Staff />
            </Suspense>
          }
        />
        <Route
          path="analytics"
          element={
            <Suspense fallback={<RouteFallback />}>
              <Analytics />
            </Suspense>
          }
        />
      </Route>
    </Routes>
  );
}
