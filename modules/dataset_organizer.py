# YOLOE自动标注系统 - 数据集组织模块

import os
import shutil
import random
from typing import List, Dict, Tuple
import numpy as np

class DatasetOrganizer:
    """
    数据集组织器，用于将标注好的图像和标签按照YOLO数据集格式组织
    YOLO数据集标准结构：
    datasets/
        └── bvn/
            ├── images/
            │   ├── train/
            │   ├── val/
            │   └── test/
            └── labels/
                ├── train/
                ├── val/
                └── test/
    """
    
    def __init__(self, image_browser, annotation_display):
        """
        初始化数据集组织器
        
        Args:
            image_browser (ImageBrowser): 图像浏览器实例
            annotation_display (AnnotationDisplay): 标注显示实例
        """
        self.image_browser = image_browser
        self.annotation_display = annotation_display
        
    def organize_dataset(self, output_dir: str, ratios: Dict[str, float] = None, 
                       random_seed: int = 42, copy_files: bool = True, progress_callback=None) -> bool:
        """
        组织数据集
        
        Args:
            output_dir (str): 输出数据集根目录
            ratios (Dict[str, float], optional): 训练集、验证集、测试集的比例
            random_seed (int, optional): 随机种子，用于确保结果可复现
            copy_files (bool, optional): 是否复制文件，False则创建符号链接
            progress_callback (callable, optional): 进度回调函数
            
        Returns:
            bool: 组织成功返回True，否则返回False
        """
        try:
            # 设置默认比例
            if ratios is None:
                ratios = {'train': 0.7, 'val': 0.2, 'test': 0.1}
            
            # 验证比例和为1
            total_ratio = sum(ratios.values())
            if abs(total_ratio - 1.0) > 1e-6:
                raise ValueError("数据集比例之和必须为1")
            
            # 获取当前图像文件列表
            image_files = self.image_browser.image_files
            if not image_files:
                raise ValueError("没有可组织的图像文件")
            
            # 过滤出带有标签的图像文件和无标签的图像文件
            labeled_image_files = []
            blank_image_files = []
            for image_path in image_files:
                label_path = os.path.splitext(image_path)[0] + '.txt'
                if os.path.exists(label_path) and os.path.getsize(label_path) > 0:
                    labeled_image_files.append(image_path)
                else:
                    blank_image_files.append(image_path)
            
            # 创建数据集目录结构 (datasets/bvn/)
            self._create_dataset_structure(output_dir)
            
            # 处理带有标签的图像文件
            if labeled_image_files:
                # 随机打乱图像列表
                random.seed(random_seed)
                random.shuffle(labeled_image_files)
                
                # 划分数据集
                train_files, val_files, test_files = self._split_dataset(labeled_image_files, ratios)
                
                # 计算总文件数，用于进度条
                total_files = len(labeled_image_files)
                
                # 构建完整的bvn目录路径
                bvn_dir = os.path.join(output_dir, 'datasets', 'bvn')
                
                # 复制或链接文件，带有进度回调
                processed = 0
                processed += self._copy_files(train_files, os.path.join(bvn_dir, 'images', 'train'), 
                                           os.path.join(bvn_dir, 'labels', 'train'), copy_files, 
                                           progress_callback, processed, total_files)
                processed += self._copy_files(val_files, os.path.join(bvn_dir, 'images', 'val'), 
                                           os.path.join(bvn_dir, 'labels', 'val'), copy_files, 
                                           progress_callback, processed, total_files)
                processed += self._copy_files(test_files, os.path.join(bvn_dir, 'images', 'test'), 
                                           os.path.join(bvn_dir, 'labels', 'test'), copy_files, 
                                           progress_callback, processed, total_files)
            
            # 处理被过滤的图片 - 复制到与datasets同级的blank文件夹
            if blank_image_files:
                self._copy_blank_files(blank_image_files, output_dir, copy_files)
            
            return True
        except Exception as e:
            print(f"数据集组织失败: {e}")
            return False
    
    def _create_dataset_structure(self, output_dir: str):
        """
        创建YOLO数据集标准目录结构
        
        Args:
            output_dir (str): 输出数据集根目录
        """
        # 创建完整目录结构: datasets/bvn/images/ 和 datasets/bvn/labels/
        bvn_dir = os.path.join(output_dir, 'datasets', 'bvn')
        
        # 确保目录存在
        os.makedirs(bvn_dir, exist_ok=True)
        
        # 创建images和labels目录下的子目录
        for split in ['train', 'val', 'test']:
            os.makedirs(os.path.join(bvn_dir, 'images', split), exist_ok=True)
            os.makedirs(os.path.join(bvn_dir, 'labels', split), exist_ok=True)
    
    def _split_dataset(self, image_files: List[str], ratios: Dict[str, float]) -> Tuple[List[str], List[str], List[str]]:
        """
        按比例划分数据集
        
        Args:
            image_files (List[str]): 图像文件列表
            ratios (Dict[str, float]): 划分比例
            
        Returns:
            Tuple[List[str], List[str], List[str]]: 训练集、验证集、测试集的图像文件列表
        """
        total_files = len(image_files)
        
        # 计算各数据集大小
        train_size = int(total_files * ratios['train'])
        val_size = int(total_files * ratios['val'])
        test_size = total_files - train_size - val_size
        
        # 划分数据集
        train_files = image_files[:train_size]
        val_files = image_files[train_size:train_size+val_size]
        test_files = image_files[train_size+val_size:]
        
        return train_files, val_files, test_files
    
    def _copy_files(self, image_files: List[str], image_dest_dir: str, label_dest_dir: str, copy_files: bool = True, 
                   progress_callback=None, start_progress=0, total_progress=0) -> int:
        """
        复制或链接图像和标签文件到目标目录
        
        Args:
            image_files (List[str]): 图像文件列表
            image_dest_dir (str): 图像目标目录
            label_dest_dir (str): 标签目标目录
            copy_files (bool, optional): 是否复制文件，False则创建符号链接
            progress_callback (callable, optional): 进度回调函数
            start_progress (int, optional): 开始进度
            total_progress (int, optional): 总进度
            
        Returns:
            int: 处理的文件数量
        """
        processed = 0
        for image_path in image_files:
            # 构建标签文件路径
            label_path = os.path.splitext(image_path)[0] + '.txt'
            
            # 构建目标路径
            image_name = os.path.basename(image_path)
            label_name = os.path.basename(label_path)
            
            dest_image_path = os.path.join(image_dest_dir, image_name)
            dest_label_path = os.path.join(label_dest_dir, label_name)
            
            # 复制或链接图像文件
            if copy_files:
                shutil.copy2(image_path, dest_image_path)
            else:
                # 创建符号链接
                if os.path.exists(dest_image_path):
                    os.unlink(dest_image_path)
                os.symlink(image_path, dest_image_path)
            
            # 复制或链接标签文件（如果存在）
            if os.path.exists(label_path):
                if copy_files:
                    shutil.copy2(label_path, dest_label_path)
                else:
                    if os.path.exists(dest_label_path):
                        os.unlink(dest_label_path)
                    os.symlink(label_path, dest_label_path)
            
            processed += 1
            # 更新进度
            if progress_callback and total_progress > 0:
                current_progress = start_progress + processed
                progress_callback(current_progress, total_progress)
        
        return processed
        
    def _copy_blank_files(self, image_files: List[str], output_dir: str, copy_files: bool = True) -> int:
        """
        复制或链接无标签图像文件到blank目录
        
        Args:
            image_files (List[str]): 无标签图像文件列表
            output_dir (str): 输出数据集根目录
            copy_files (bool, optional): 是否复制文件，False则创建符号链接
            
        Returns:
            int: 处理的文件数量
        """
        # 创建blank目录（与datasets同级）
        blank_dir = os.path.join(output_dir, 'blank')
        os.makedirs(blank_dir, exist_ok=True)
        
        processed = 0
        for image_path in image_files:
            # 构建目标路径
            image_name = os.path.basename(image_path)
            dest_image_path = os.path.join(blank_dir, image_name)
            
            # 复制或链接图像文件
            if copy_files:
                shutil.copy2(image_path, dest_image_path)
            else:
                # 创建符号链接
                if os.path.exists(dest_image_path):
                    os.unlink(dest_image_path)
                os.symlink(image_path, dest_image_path)
            
            processed += 1
        
        return processed
    
    def get_dataset_summary(self, output_dir: str) -> Dict[str, Dict[str, int]]:
        """
        获取数据集统计信息
        
        Args:
            output_dir (str): 数据集根目录
            
        Returns:
            Dict[str, Dict[str, int]]: 数据集统计信息，包含train、val、test和blank
        """
        summary = {}
        
        # 构建完整的bvn目录路径
        bvn_dir = os.path.join(output_dir, 'datasets', 'bvn')
        
        # 统计train、val、test数据集
        for split in ['train', 'val', 'test']:
            image_dir = os.path.join(bvn_dir, 'images', split)
            label_dir = os.path.join(bvn_dir, 'labels', split)
            
            # 统计图像数量
            image_count = 0
            if os.path.exists(image_dir):
                image_count = len([f for f in os.listdir(image_dir) if os.path.isfile(os.path.join(image_dir, f))])
            
            # 统计标签数量
            label_count = 0
            if os.path.exists(label_dir):
                label_count = len([f for f in os.listdir(label_dir) if os.path.isfile(os.path.join(label_dir, f))])
            
            summary[split] = {
                'images': image_count,
                'labels': label_count
            }
        
        # 统计blank文件夹
        blank_dir = os.path.join(output_dir, 'blank')
        blank_image_count = 0
        if os.path.exists(blank_dir):
            blank_image_count = len([f for f in os.listdir(blank_dir) if os.path.isfile(os.path.join(blank_dir, f))])
        
        summary['blank'] = {
            'images': blank_image_count,
            'labels': 0  # blank文件夹没有标签
        }
        
        return summary
