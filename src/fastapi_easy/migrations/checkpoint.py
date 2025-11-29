"""Checkpoint 机制 - 支持迁移断点续传"""
import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CheckpointRecord:
    """检查点记录"""
    version: str  # 迁移版本
    migration_id: str  # 迁移 ID
    status: str  # 状态: pending, in_progress, completed, failed
    started_at: str  # 开始时间
    completed_at: Optional[str] = None  # 完成时间
    error: Optional[str] = None  # 错误信息
    progress: int = 0  # 进度百分比 (0-100)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class CheckpointManager:
    """检查点管理器"""
    
    def __init__(self, checkpoint_dir: str = ".fastapi_easy_checkpoints"):
        self.checkpoint_dir = checkpoint_dir
        self._ensure_dir()
    
    def _ensure_dir(self) -> None:
        """确保检查点目录存在"""
        if not os.path.exists(self.checkpoint_dir):
            os.makedirs(self.checkpoint_dir)
            logger.info(f"创建检查点目录: {self.checkpoint_dir}")
    
    def _get_checkpoint_file(self, migration_id: str) -> str:
        """获取检查点文件路径"""
        return os.path.join(self.checkpoint_dir, f"{migration_id}.json")
    
    def save_checkpoint(self, record: CheckpointRecord) -> bool:
        """保存检查点"""
        try:
            checkpoint_file = self._get_checkpoint_file(record.migration_id)
            with open(checkpoint_file, 'w') as f:
                json.dump(record.to_dict(), f, indent=2)
            logger.info(f"保存检查点: {record.migration_id} ({record.status})")
            return True
        except Exception as e:
            logger.error(f"保存检查点失败: {e}")
            return False
    
    def load_checkpoint(self, migration_id: str) -> Optional[CheckpointRecord]:
        """加载检查点"""
        try:
            checkpoint_file = self._get_checkpoint_file(migration_id)
            if not os.path.exists(checkpoint_file):
                return None
            
            with open(checkpoint_file, 'r') as f:
                data = json.load(f)
            
            return CheckpointRecord(**data)
        except Exception as e:
            logger.error(f"加载检查点失败: {e}")
            return None
    
    def delete_checkpoint(self, migration_id: str) -> bool:
        """删除检查点"""
        try:
            checkpoint_file = self._get_checkpoint_file(migration_id)
            if os.path.exists(checkpoint_file):
                os.remove(checkpoint_file)
                logger.info(f"删除检查点: {migration_id}")
            return True
        except Exception as e:
            logger.error(f"删除检查点失败: {e}")
            return False
    
    def get_pending_migrations(self) -> List[CheckpointRecord]:
        """获取待处理的迁移"""
        pending = []
        try:
            for filename in os.listdir(self.checkpoint_dir):
                if filename.endswith('.json'):
                    migration_id = filename[:-5]
                    checkpoint = self.load_checkpoint(migration_id)
                    if checkpoint and checkpoint.status in ['pending', 'in_progress']:
                        pending.append(checkpoint)
        except Exception as e:
            logger.error(f"获取待处理迁移失败: {e}")
        
        return pending
    
    def get_failed_migrations(self) -> List[CheckpointRecord]:
        """获取失败的迁移"""
        failed = []
        try:
            for filename in os.listdir(self.checkpoint_dir):
                if filename.endswith('.json'):
                    migration_id = filename[:-5]
                    checkpoint = self.load_checkpoint(migration_id)
                    if checkpoint and checkpoint.status == 'failed':
                        failed.append(checkpoint)
        except Exception as e:
            logger.error(f"获取失败迁移失败: {e}")
        
        return failed
    
    def mark_in_progress(self, version: str, migration_id: str) -> bool:
        """标记为进行中"""
        record = CheckpointRecord(
            version=version,
            migration_id=migration_id,
            status='in_progress',
            started_at=datetime.utcnow().isoformat()
        )
        return self.save_checkpoint(record)
    
    def mark_completed(self, migration_id: str, progress: int = 100) -> bool:
        """标记为已完成"""
        checkpoint = self.load_checkpoint(migration_id)
        if not checkpoint:
            logger.warning(f"检查点不存在: {migration_id}")
            return False
        
        checkpoint.status = 'completed'
        checkpoint.completed_at = datetime.utcnow().isoformat()
        checkpoint.progress = progress
        return self.save_checkpoint(checkpoint)
    
    def mark_failed(self, migration_id: str, error: str) -> bool:
        """标记为失败"""
        checkpoint = self.load_checkpoint(migration_id)
        if not checkpoint:
            logger.warning(f"检查点不存在: {migration_id}")
            return False
        
        checkpoint.status = 'failed'
        checkpoint.error = error
        checkpoint.completed_at = datetime.utcnow().isoformat()
        return self.save_checkpoint(checkpoint)
    
    def update_progress(self, migration_id: str, progress: int) -> bool:
        """更新进度"""
        checkpoint = self.load_checkpoint(migration_id)
        if not checkpoint:
            logger.warning(f"检查点不存在: {migration_id}")
            return False
        
        checkpoint.progress = min(progress, 100)
        return self.save_checkpoint(checkpoint)
    
    def cleanup_completed(self, keep_days: int = 7) -> int:
        """清理已完成的检查点"""
        import time
        cleaned = 0
        current_time = time.time()
        cutoff_time = current_time - (keep_days * 24 * 60 * 60)
        
        try:
            for filename in os.listdir(self.checkpoint_dir):
                if filename.endswith('.json'):
                    checkpoint_file = os.path.join(self.checkpoint_dir, filename)
                    file_time = os.path.getmtime(checkpoint_file)
                    
                    if file_time < cutoff_time:
                        migration_id = filename[:-5]
                        checkpoint = self.load_checkpoint(migration_id)
                        
                        if checkpoint and checkpoint.status == 'completed':
                            os.remove(checkpoint_file)
                            cleaned += 1
                            logger.info(f"清理检查点: {migration_id}")
        except Exception as e:
            logger.error(f"清理检查点失败: {e}")
        
        return cleaned
    
    def get_statistics(self) -> Dict[str, int]:
        """获取统计信息"""
        stats = {
            'total': 0,
            'pending': 0,
            'in_progress': 0,
            'completed': 0,
            'failed': 0
        }
        
        try:
            for filename in os.listdir(self.checkpoint_dir):
                if filename.endswith('.json'):
                    migration_id = filename[:-5]
                    checkpoint = self.load_checkpoint(migration_id)
                    if checkpoint:
                        stats['total'] += 1
                        stats[checkpoint.status] = stats.get(checkpoint.status, 0) + 1
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
        
        return stats
