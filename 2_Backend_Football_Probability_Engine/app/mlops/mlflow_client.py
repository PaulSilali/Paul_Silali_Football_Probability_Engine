"""
MLflow Client for Experiment Tracking and Model Registry
"""
try:
    import mlflow
    import mlflow.sklearn
    from mlflow.tracking import MlflowClient
    from mlflow.store.artifact.runs_artifact_repo import RunsArtifactRepository
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    mlflow = None
    MlflowClient = None

from typing import Dict, List, Optional, Any
import logging
from datetime import datetime
import os

logger = logging.getLogger(__name__)

# MLflow Configuration
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
MLFLOW_ARTIFACT_ROOT = os.getenv("MLFLOW_ARTIFACT_ROOT", "./mlruns")

# Initialize MLflow (only if available)
if MLFLOW_AVAILABLE:
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)


class MLflowModelRegistry:
    """Manages model lifecycle with MLflow"""
    
    def __init__(self):
        self.client = MlflowClient(tracking_uri=MLFLOW_TRACKING_URI)
        logger.info(f"MLflow client initialized with tracking URI: {MLFLOW_TRACKING_URI}")
        
    def create_experiment(self, name: str, description: str = "") -> str:
        """Create MLflow experiment"""
        if not MLFLOW_AVAILABLE:
            raise ImportError("MLflow is not installed")
        
        try:
            experiment_id = self.client.create_experiment(
                name=name,
                artifact_location=f"{MLFLOW_ARTIFACT_ROOT}/{name}",
                tags={"description": description}
            )
            logger.info(f"Created experiment: {name} (ID: {experiment_id})")
            return experiment_id
        except Exception as e:
            # Experiment exists
            logger.info(f"Experiment {name} already exists, retrieving...")
            experiment = self.client.get_experiment_by_name(name)
            if experiment:
                return experiment.experiment_id
            raise ValueError(f"Failed to create or retrieve experiment: {name}")
    
    def log_training_run(
        self,
        experiment_name: str,
        model: Any,
        params: Dict[str, Any],
        metrics: Dict[str, float],
        artifacts: Optional[Dict[str, str]] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Log a training run to MLflow
        
        Args:
            experiment_name: Name of experiment
            model: Trained model object (can be dict for custom models)
            params: Hyperparameters
            metrics: Validation metrics (brier_score, log_loss, accuracy, etc.)
            artifacts: Additional artifacts to log (file paths)
            tags: Additional tags
            
        Returns:
            run_id: MLflow run ID
        """
        experiment_id = self.create_experiment(experiment_name)
        
        with mlflow.start_run(experiment_id=experiment_id):
            # Log parameters
            mlflow.log_params(params)
            
            # Log metrics
            mlflow.log_metrics(metrics)
            
            # Log tags
            if tags:
                mlflow.set_tags(tags)
            
            # Log model (if it's a scikit-learn compatible model)
            try:
                if hasattr(model, 'predict') or isinstance(model, dict):
                    # For custom models, log as artifact
                    import json
                    import tempfile
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                        json.dump(model if isinstance(model, dict) else {"type": "custom"}, f)
                        mlflow.log_artifact(f.name, "model")
                else:
                    mlflow.sklearn.log_model(model, "model")
            except Exception as e:
                logger.warning(f"Could not log model to MLflow: {e}")
                # Log model metadata instead
                mlflow.log_dict({"model_type": str(type(model))}, "model_metadata.json")
            
            # Log additional artifacts
            if artifacts:
                for name, artifact_path in artifacts.items():
                    if os.path.exists(artifact_path):
                        mlflow.log_artifact(artifact_path, name)
            
            run_id = mlflow.active_run().info.run_id
            logger.info(f"Logged training run: {run_id} to experiment: {experiment_name}")
            return run_id
    
    def load_production_model(self, model_name: str = "dixon_coles_production") -> Any:
        """Load current production model from MLflow registry"""
        if not MLFLOW_AVAILABLE:
            raise ImportError("MLflow is not installed")
        
        try:
            model = mlflow.pyfunc.load_model(f"models:/{model_name}/Production")
            logger.info(f"Loaded production model: {model_name}")
            return model
        except Exception as e:
            logger.warning(f"Could not load production model: {e}")
            # Fallback to latest version
            try:
                latest_version = self.client.get_latest_versions(model_name, stages=["None"])
                if latest_version:
                    model = mlflow.pyfunc.load_model(
                        f"models:/{model_name}/{latest_version[0].version}"
                    )
                    logger.info(f"Loaded latest model version: {latest_version[0].version}")
                    return model
            except Exception as e2:
                logger.error(f"Could not load any model version: {e2}")
            raise ValueError(f"No model found: {model_name}")
    
    def promote_to_production(
        self, 
        model_name: str, 
        version: str,
        archive_current: bool = True
    ):
        """Promote model version to production"""
        if not MLFLOW_AVAILABLE:
            raise ImportError("MLflow is not installed")
        
        try:
            # Archive current production if requested
            if archive_current:
                for mv in self.client.get_latest_versions(model_name, stages=["Production"]):
                    self.client.transition_model_version_stage(
                        name=model_name,
                        version=mv.version,
                        stage="Archived"
                    )
                    logger.info(f"Archived model version: {mv.version}")
            
            # Promote new version
            self.client.transition_model_version_stage(
                name=model_name,
                version=version,
                stage="Production"
            )
            logger.info(f"Promoted model {model_name} version {version} to Production")
        except Exception as e:
            logger.error(f"Error promoting model to production: {e}")
            raise
    
    def get_experiment_history(self, experiment_name: str) -> List[Dict]:
        """Get all runs for an experiment"""
        if not MLFLOW_AVAILABLE:
            raise ImportError("MLflow is not installed")
        
        try:
            experiment = self.client.get_experiment_by_name(experiment_name)
            if not experiment:
                return []
            
            runs = self.client.search_runs(
                experiment_ids=[experiment.experiment_id],
                order_by=["metrics.brier_score ASC"]
            )
            
            return [
                {
                    "run_id": run.info.run_id,
                    "start_time": datetime.fromtimestamp(run.info.start_time / 1000).isoformat(),
                    "status": run.info.status,
                    "metrics": {k: v for k, v in run.data.metrics.items()},
                    "params": {k: v for k, v in run.data.params.items()},
                }
                for run in runs
            ]
        except Exception as e:
            logger.error(f"Error getting experiment history: {e}")
            return []
    
    def get_best_model(self, experiment_name: str, metric: str = "brier_score") -> Optional[Dict]:
        """Get best model from experiment based on metric"""
        if not MLFLOW_AVAILABLE:
            raise ImportError("MLflow is not installed")
        
        try:
            experiment = self.client.get_experiment_by_name(experiment_name)
            if not experiment:
                return None
            
            runs = self.client.search_runs(
                experiment_ids=[experiment.experiment_id],
                order_by=[f"metrics.{metric} ASC"],
                max_results=1
            )
            
            if runs:
                run = runs[0]
                return {
                    "run_id": run.info.run_id,
                    "metrics": {k: v for k, v in run.data.metrics.items()},
                    "params": {k: v for k, v in run.data.params.items()},
                }
            return None
        except Exception as e:
            logger.error(f"Error getting best model: {e}")
            return None
    
    def register_model(
        self,
        run_id: str,
        model_name: str,
        description: str = ""
    ) -> str:
        """Register a model from a run"""
        if not MLFLOW_AVAILABLE:
            raise ImportError("MLflow is not installed")
        
        try:
            model_uri = f"runs:/{run_id}/model"
            mv = self.client.create_model_version(
                name=model_name,
                source=model_uri,
                description=description
            )
            logger.info(f"Registered model: {model_name} version {mv.version}")
            return mv.version
        except Exception as e:
            logger.error(f"Error registering model: {e}")
            raise

