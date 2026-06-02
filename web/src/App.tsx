import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { SettingsProvider } from './contexts/SettingsContext';
import BottomNav from './components/BottomNav';
import CapturePage from './pages/CapturePage';
import AskPage from './pages/AskPage';
import BriefPage from './pages/BriefPage';
import InboxPage from './pages/InboxPage';
import HealthPage from './pages/HealthPage';
import SettingsPage from './pages/SettingsPage';

export default function App() {
  return (
    <SettingsProvider>
      <BrowserRouter>
        <div className="flex min-h-screen flex-col bg-bg text-text">
          <div className="flex-1">
            <Routes>
              <Route path="/" element={<Navigate to="/capture" replace />} />
              <Route path="/capture" element={<CapturePage />} />
              <Route path="/ask" element={<AskPage />} />
              <Route path="/brief" element={<BriefPage />} />
              <Route path="/inbox" element={<InboxPage />} />
              <Route path="/health" element={<HealthPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Routes>
          </div>
          <BottomNav />
        </div>
      </BrowserRouter>
    </SettingsProvider>
  );
}