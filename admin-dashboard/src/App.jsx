import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import Analytics from "./pages/Analytics";
import Billing from "./pages/Billing";
import Broadcast from "./pages/Broadcast";
import Calendar from "./pages/Calendar";
import ConversationView from "./pages/ConversationView";
import Inbox from "./pages/Inbox";
import Login from "./pages/Login";
import Permissions from "./pages/Permissions";
import Programmes from "./pages/Programmes";
import ReportCards from "./pages/ReportCards";
import Staff from "./pages/Staff";
import Tickets from "./pages/Tickets";

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
        <Route path="inbox" element={<Inbox />} />
        <Route
          path="conversations/:conversationId"
          element={<ConversationView />}
        />
        <Route path="tickets" element={<Tickets />} />
        <Route path="billing" element={<Billing />} />
        <Route path="programmes" element={<Programmes />} />
        <Route path="broadcast" element={<Broadcast />} />
        <Route path="calendar" element={<Calendar />} />
        <Route path="permissions" element={<Permissions />} />
        <Route path="report-cards" element={<ReportCards />} />
        <Route path="staff" element={<Staff />} />
        <Route path="analytics" element={<Analytics />} />
      </Route>
    </Routes>
  );
}
