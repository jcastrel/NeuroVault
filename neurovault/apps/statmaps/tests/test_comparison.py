from neurovault.apps.statmaps.models import Image, Comparison, Similarity, User, Collection, StatisticMap
from neurovault.apps.statmaps.tasks import save_voxelwise_pearson_similarity, get_images_by_ordered_id
from django.core.files.uploadedfile import SimpleUploadedFile
from neurovault.apps.statmaps.utils import split_afni4D_to_3D
from django.shortcuts import get_object_or_404
from django.db import IntegrityError
from django.test import TestCase
import tempfile
import nibabel
import shutil
import errno
import os

class ComparisonTestCase(TestCase):
    pk1 = None
    pk1_copy = None
    pk2 = None
    pk3 = None
    pearson_metric = None
    
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        app_path = os.path.abspath(os.path.dirname(__file__))
        self.u1 = User.objects.create(username='neurovault')
        comparisonCollection = Collection(name='comparisonCollection',owner=self.u1)
        comparisonCollection.save()
        
        image1 = StatisticMap(name='image1', description='',collection=comparisonCollection)
        image1.file = SimpleUploadedFile('VentralFrontal_thr75_summaryimage_2mm.nii.gz', file(os.path.join(app_path,'test_data/api/VentralFrontal_thr75_summaryimage_2mm.nii.gz')).read())
        image1.save()
        self.pk1 = image1.id
        
        # Image 2 is equivalent to 1, so pearson should be 1.0
        image2 = StatisticMap(name='image1_copy', description='',collection=comparisonCollection)
        image2.file = SimpleUploadedFile('VentralFrontal_thr75_summaryimage_2mm.nii.gz', file(os.path.join(app_path,'test_data/api/VentralFrontal_thr75_summaryimage_2mm.nii.gz')).read())
        image2.save()
        self.pk1_copy = image2.id
        
        bricks = split_afni4D_to_3D(nibabel.load(os.path.join(app_path,'test_data/TTatlas.nii.gz')),tmp_dir=self.tmpdir)
        
        image3 = StatisticMap(name='image2', description='',collection=comparisonCollection)
        image3.file = SimpleUploadedFile('brik1.nii.gz', file(bricks[0][1]).read())
        image3.save()
        self.pk2 = image3.id
        
        image4 = StatisticMap(name='image3', description='',collection=comparisonCollection)
        image4.file = SimpleUploadedFile('brik2.nii.gz', file(bricks[1][1]).read())
        image4.save()
        self.pk3 = image4.id
        
        self.pearson_metric = Similarity(similarity_metric="pearson product-moment correlation coefficient",
                                         transformation="voxelwise",
                                         metric_ontology_iri="http://webprotege.stanford.edu/RCS8W76v1MfdvskPLiOdPaA",
                                         transformation_ontology_iri="http://webprotege.stanford.edu/R87C6eFjEftkceScn1GblDL")
        self.pearson_metric.save()
        
    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_save_pearson_similarity(self):
        # Should be 1
        print "Testing %s vs. %s: same images, different ids" %(self.pk1,self.pk1_copy)
        save_voxelwise_pearson_similarity(self.pk1,self.pk1_copy)
 
        # Should not be saved
        with self.assertRaises(Exception):
          print "Testing %s vs. %s: same pks, success is raising exception" %(self.pk1,self.pk1)
          save_voxelwise_pearson_similarity(self.pk1,self.pk1)

        print "Testing %s vs. %s, different image set 1" %(self.pk1,self.pk2)
        save_voxelwise_pearson_similarity(self.pk1,self.pk2)

        print "Testing %s vs. %s, different image set 2" %(self.pk2,self.pk3)
        save_voxelwise_pearson_similarity(self.pk2,self.pk3)

        # Should not exist
        print "Success for this test means there are no comparisons returned."
        image1, image1_copy = get_images_by_ordered_id(self.pk1, self.pk1)
        comparison = Comparison.objects.filter(image1=image1,image2=image1_copy,similarity_metric=self.pearson_metric)
        self.assertEqual(len(comparison), 0)

        # Should be 1        
        print "Success for this test means a score of 1.0"
        image1, image2 = get_images_by_ordered_id(self.pk1, self.pk1_copy)
        comparison = Comparison.objects.filter(image1=image1,image2=image2,similarity_metric=self.pearson_metric)
        self.assertEqual(len(comparison), 1)
        self.assertAlmostEqual(comparison[0].similarity_score, 1.0)

        print "Success for the remaining tests means a specific comparison score."
        image1, image2 = get_images_by_ordered_id(self.pk1, self.pk2)
        comparison = Comparison.objects.filter(image1=image1,image2=image2,similarity_metric=self.pearson_metric)
        self.assertEqual(len(comparison), 1)
        print comparison[0].similarity_score
        self.assertAlmostEqual(comparison[0].similarity_score, 0.0196480800969)

        image2, image3 = get_images_by_ordered_id(self.pk3, self.pk2)
        comparison = Comparison.objects.filter(image1=image2,image2=image3,similarity_metric=self.pearson_metric)
        self.assertEqual(len(comparison), 1)
        print comparison[0].similarity_score
        self.assertAlmostEqual(comparison[0].similarity_score, 0.312548260436)
