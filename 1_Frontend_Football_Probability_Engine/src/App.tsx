import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";
import { AppShell } from "@/components/layout/AppShell";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";
import Index from "./pages/Index";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import JackpotInput from "./pages/JackpotInput";
import ProbabilityOutput from "./pages/ProbabilityOutput";
import SetsComparison from "./pages/SetsComparison";
import FeatureStore from "./pages/FeatureStore";
import Calibration from "./pages/Calibration";
import Explainability from "./pages/Explainability";
import ModelHealth from "./pages/ModelHealth";
import System from "./pages/System";
import DataIngestion from "./pages/DataIngestion";
import MLTraining from "./pages/MLTraining";
import DataCleaning from "./pages/DataCleaning";
import TrainingDataContract from "./pages/TrainingDataContract";
import JackpotValidation from "./pages/JackpotValidation";
import ResponsibleGamblingPage from "./pages/ResponsibleGamblingPage";
import TicketConstruction from "./pages/TicketConstruction";
import SureBet from "./pages/SureBet";
import Backtesting from "./pages/Backtesting";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <AuthProvider>
        <BrowserRouter
          future={{
            v7_startTransition: true,
            v7_relativeSplatPath: true,
          }}
        >
          <Routes>
            {/* Public routes */}
            <Route path="/" element={<Index />} />
            <Route path="/login" element={<Login />} />
            
            {/* Protected routes */}
            <Route
              path="/*"
              element={
                <ProtectedRoute>
                  <AppShell>
                    <Routes>
                      <Route path="/dashboard" element={<Dashboard />} />
                      <Route path="/data-ingestion" element={<DataIngestion />} />
                      <Route path="/data-cleaning" element={<DataCleaning />} />
                      <Route path="/training-data-contract" element={<TrainingDataContract />} />
                      <Route path="/ml-training" element={<MLTraining />} />
                      <Route path="/jackpot-input" element={<JackpotInput />} />
                      <Route path="/probability-output" element={<ProbabilityOutput />} />
                      <Route path="/sets-comparison" element={<SetsComparison />} />
                      <Route path="/ticket-construction" element={<TicketConstruction />} />
                      <Route path="/sure-bet" element={<SureBet />} />
                      <Route path="/jackpot-validation" element={<JackpotValidation />} />
                      <Route path="/backtesting" element={<Backtesting />} />
                      <Route path="/feature-store" element={<FeatureStore />} />
                      <Route path="/calibration" element={<Calibration />} />
                      <Route path="/explainability" element={<Explainability />} />
                      <Route path="/model-health" element={<ModelHealth />} />
                      <Route path="/responsible-gambling" element={<ResponsibleGamblingPage />} />
                      <Route path="/system" element={<System />} />
                      <Route path="*" element={<NotFound />} />
                    </Routes>
                  </AppShell>
                </ProtectedRoute>
              }
            />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
