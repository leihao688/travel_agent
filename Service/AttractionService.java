package org.example.travel_commend.Service;


import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.IService;
import jakarta.validation.Valid;
import org.example.travel_commend.VO.AttractionVO;
import org.example.travel_commend.dto.AttractionDTO;
import org.example.travel_commend.dto.AttractionQueryDTO;
import org.example.travel_commend.dto.Result;
import org.example.travel_commend.entity.Attraction;

import java.util.List;


public interface AttractionService extends IService<Attraction> {
    Result<Void> createAttraction(@Valid AttractionDTO attractionDTO);

    Result<Void> updateAttraction(Long id, @Valid AttractionDTO attractionDTO);

    Result<Void> deleteAttraction(Long id);

    void increaseViewCount(Long id);

    Result<AttractionVO> getAttractionById(Long id);

    Result<Page<AttractionVO>> queryAttractions(AttractionQueryDTO queryDTO);

    Result<List<AttractionVO>> getHotAttractions();
    Result<AttractionVO> getAttractionDetail(Long id);
}
