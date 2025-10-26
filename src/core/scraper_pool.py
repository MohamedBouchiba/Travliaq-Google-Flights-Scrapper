# src/core/scraper_pool.py - VERSION AVEC DEBUG

import subprocess
import json
import tempfile
from pathlib import Path
from typing import Dict, Optional
import threading
from dataclasses import dataclass
from datetime import datetime
import uuid
import sys

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ScrapeJob:
    """Job de scraping"""
    job_id: str
    origin: str
    destination: str
    start_date: str
    end_date: str
    created_at: datetime
    process: Optional[subprocess.Popen] = None
    result_file: Optional[Path] = None


class ScraperPool:
    """Gestionnaire de scrapers avec subprocess"""

    def __init__(self, max_workers: int = 10):
        self.jobs: Dict[str, ScrapeJob] = {}
        self.lock = threading.Lock()
        self.temp_dir = Path(tempfile.gettempdir()) / "travliaq_scraper"
        self.temp_dir.mkdir(exist_ok=True, parents=True)

        logger.info(f"✓ ScraperPool initialisé (temp_dir: {self.temp_dir})")

    def submit_scrape(
            self,
            origin: str,
            destination: str,
            start_date: str,
            end_date: str
    ) -> str:
        """Lance un subprocess de scraping"""
        job_id = str(uuid.uuid4())[:8]
        result_file = self.temp_dir / f"result_{job_id}.json"

        job = ScrapeJob(
            job_id=job_id,
            origin=origin,
            destination=destination,
            start_date=start_date,
            end_date=end_date,
            created_at=datetime.now(),
            result_file=result_file
        )

        # Chemin du worker
        script_path = Path(__file__).parent.parent.parent / "scripts" / "scraper_worker.py"

        if not script_path.exists():
            raise FileNotFoundError(f"Worker script introuvable: {script_path}")

        # Commande
        cmd = [
            sys.executable,
            str(script_path),
            origin,
            destination,
            start_date,
            end_date,
            str(result_file),
            job_id
        ]

        logger.info(f"Job {job_id}: Lancement subprocess pour {origin}->{destination}")
        logger.debug(f"Job {job_id}: Commande: {' '.join(cmd)}")

        try:
            # Lancer le subprocess
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )

            job.process = process

            with self.lock:
                self.jobs[job_id] = job

            logger.info(f"Job {job_id}: Subprocess PID={process.pid} lancé")

        except Exception as e:
            logger.error(f"Job {job_id}: Erreur lancement subprocess: {e}")
            raise

        return job_id

    def wait_for_job(self, job_id: str, timeout: Optional[float] = None) -> Dict:
        """Attend qu'un job se termine"""
        with self.lock:
            job = self.jobs.get(job_id)

        if not job:
            raise ValueError(f"Job {job_id} introuvable")

        if not job.process:
            raise ValueError(f"Job {job_id} n'a pas de process")

        logger.info(f"Job {job_id}: Attente du résultat (timeout={timeout}s)...")

        try:
            # Attendre la fin
            stdout, stderr = job.process.communicate(timeout=timeout)
            returncode = job.process.returncode

            logger.info(f"Job {job_id}: Process terminé avec code {returncode}")

            # Logger la sortie (pour debug)
            if stdout:
                logger.debug(f"Job {job_id} STDOUT:\n{stdout}")
            if stderr:
                logger.warning(f"Job {job_id} STDERR:\n{stderr}")

            # Lire le résultat
            if job.result_file and job.result_file.exists():
                with open(job.result_file, 'r', encoding='utf-8') as f:
                    result = json.load(f)

                # Vérifier si erreur
                if "error" in result:
                    error_msg = result["error"]
                    traceback_msg = result.get("traceback", "")
                    logger.error(f"Job {job_id}: Erreur dans worker:\n{error_msg}\n{traceback_msg}")
                    raise Exception(f"Worker error: {error_msg}")

                # Nettoyer le fichier
                try:
                    job.result_file.unlink()
                except:
                    pass

                logger.info(f"Job {job_id}: {len(result)} prix récupérés")
                return result
            else:
                raise Exception(f"Fichier de résultat introuvable: {job.result_file}")

        except subprocess.TimeoutExpired:
            logger.error(f"Job {job_id}: Timeout après {timeout}s!")
            job.process.kill()
            raise TimeoutError(f"Job {job_id} timeout")
        except Exception as e:
            logger.error(f"Job {job_id}: Erreur - {e}")
            raise

    def get_active_jobs_count(self) -> int:
        """Compte les jobs actifs"""
        with self.lock:
            return sum(
                1 for job in self.jobs.values()
                if job.process and job.process.poll() is None
            )

    def cleanup_old_jobs(self, max_age_hours: int = 24):
        """Nettoie les vieux jobs"""
        cutoff = datetime.now().timestamp() - (max_age_hours * 3600)

        with self.lock:
            to_remove = []
            for job_id, job in self.jobs.items():
                if job.created_at.timestamp() < cutoff:
                    if job.process and job.process.poll() is None:
                        job.process.kill()
                    if job.result_file and job.result_file.exists():
                        try:
                            job.result_file.unlink()
                        except:
                            pass
                    to_remove.append(job_id)

            for job_id in to_remove:
                del self.jobs[job_id]

    def shutdown(self):
        """Arrête tous les processus"""
        logger.info("Arrêt du ScraperPool...")
        with self.lock:
            for job in self.jobs.values():
                if job.process and job.process.poll() is None:
                    job.process.kill()


# Instance globale
scraper_pool = ScraperPool()